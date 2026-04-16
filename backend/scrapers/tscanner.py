"""
골프존 티스캐너 (teescanner.com) — requests 기반
- GET  https://foapi.teescanner.com/v1/area/getAllAreaList         → 지역 목록
- POST https://foapi.teescanner.com/v1/booking/getGolfclubListByGolfclub → 골프장/티타임 수 목록
  필수 파라미터: page, page_size, roundDay, tab, isScroll, orderType
"""
import html
import logging
import requests
from typing import List, Optional
from .base import BaseScraper

logger = logging.getLogger(__name__)

FOAPI = "https://foapi.teescanner.com"

# 입력 지역명 → TeeScanner 상위 지역명(step=2) 키워드 매핑
# 실제 TeeScanner 지역: 경기남부, 경기북부, 충청북부, 충청남부,
#                       경상북부, 경상남부, 전라북부, 전라남부, 강원서부, 강원동부, 제주
REGION_KEYWORDS = {
    "서울": ["경기남부", "경기북부"],   # 서울 인근 → 경기 전체
    "경기": ["경기"],                   # 경기남부, 경기북부 모두
    "인천": ["경기남부"],               # 인천권 ⊂ 경기남부
    "강원": ["강원"],                   # 강원서부, 강원동부 모두
    "충북": ["충청북"],
    "충남": ["충청남"],
    "대전": ["충청남"],                 # 대전권 ⊂ 충청남부
    "세종": ["충청남"],
    "경북": ["경상북"],
    "경남": ["경상남"],
    "대구": ["경상북"],                 # 대구권 ⊂ 경상북부
    "부산": ["경상남"],                 # 부산권 ⊂ 경상남부
    "울산": ["경상남"],
    "전북": ["전라북"],
    "전남": ["전라남"],
    "광주": ["전라남"],                 # 광주권 ⊂ 전라남부
    "제주": ["제주"],
}

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://www.teescanner.com/",
    "Origin": "https://www.teescanner.com",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ko-KR,ko;q=0.9",
}


class TScannerScraper(BaseScraper):
    name = "티스캐너"
    BASE = "https://www.teescanner.com"

    # 지역 캐시: {parent_area_name: [child_area_seq, ...]}
    _area_cache: Optional[dict] = None

    # ─── 지역 캐시 ──────────────────────────────────────────────

    def _load_area_cache(self):
        self._area_cache = {}
        try:
            resp = requests.get(f"{FOAPI}/v1/area/getAllAreaList",
                                headers=_HEADERS, timeout=10)
            raw = resp.json()

            # 실제 응답: {"result":0, "message":"", "data":[...list...]}
            area_list = raw.get("data") or []
            if isinstance(area_list, dict):
                area_list = area_list.get("areaList", [])

            # seq → {name, step, parent} 정리
            areas: dict = {}
            for a in area_list:
                seq    = a.get("area_seq")
                name   = a.get("area_name", "")
                step   = int(a.get("step", 2))     # 2: 상위지역, 3: 하위지역
                parent = a.get("parent_area_seq")
                if seq is not None:
                    areas[seq] = {"name": name, "step": step, "parent": parent}

            # step=2 상위 지역 → step=3 하위 지역 seq 목록 매핑
            for seq, info in areas.items():
                if info["step"] == 3 and info["parent"] is not None:
                    parent_info = areas.get(info["parent"], {})
                    parent_name = parent_info.get("name", "")
                    self._area_cache.setdefault(parent_name, []).append(seq)

            # 하위 지역이 없는 step=2 지역은 자신을 fallback으로 매핑
            for seq, info in areas.items():
                if info["step"] == 2 and info["name"] not in self._area_cache:
                    self._area_cache[info["name"]] = [seq]

            logger.info(f"[티스캐너] 지역 캐시: {list(self._area_cache.keys())}")
        except Exception as e:
            logger.error(f"[티스캐너] 지역 목록 로드 실패: {type(e).__name__}: {e}")
            self._area_cache = {}

    def _get_area_ids(self, regions: List[str]) -> List[int]:
        if self._area_cache is None:
            self._load_area_cache()

        if not regions:
            return []   # areaList 미전송 → 전체 검색

        area_ids: set = set()
        for region in regions:
            keywords = REGION_KEYWORDS.get(region, [region])
            for kw in keywords:
                for cached_name, ids in self._area_cache.items():
                    if kw in cached_name:
                        area_ids.update(ids)

        return list(area_ids)

    # ─── 검색 ───────────────────────────────────────────────────

    async def search(self, date: str, regions: List[str], players: int,
                     time_from: str, time_to: str) -> List[dict]:
        area_ids = self._get_area_ids(regions)
        logger.info(f"[티스캐너] 검색: date={date}, regions={regions}, "
                    f"area_ids 수={len(area_ids)}")

        session = requests.Session()
        session.headers.update(_HEADERS)

        results = []
        page = 1
        page_size = 50

        while True:
            try:
                form = {
                    "page": str(page),
                    "page_size": str(page_size),
                    "roundDay": date,           # "2026-04-25"
                    "tab": "golfcourse",
                    "isScroll": "N",
                    "orderType": "distance",    # 필수 파라미터
                }
                if area_ids:
                    form["areaList"] = ",".join(str(i) for i in area_ids)

                resp = session.post(
                    f"{FOAPI}/v1/booking/getGolfclubListByGolfclub",
                    data=form,
                    timeout=20,
                )
                raw = resp.json()

                # 실제 응답: {"result":0, "data":{"totalCnt":N, "golfclubList":[...]}}
                data_obj = raw.get("data") or {}
                if isinstance(data_obj, list):
                    clubs = data_obj
                    total_cnt = 0
                else:
                    clubs = data_obj.get("golfclubList") or []
                    total_cnt = int(data_obj.get("totalCnt") or 0)

                if not clubs:
                    logger.info(f"[티스캐너] page={page}: 결과 없음")
                    break

                logger.info(f"[티스캐너] page={page}: {len(clubs)}개 클럽 (전체 {total_cnt}개)")

                for club in clubs:
                    name     = html.unescape(club.get("golfclub_name") or "")
                    region   = html.unescape(
                        club.get("area_name1") or club.get("area_name") or
                        (regions[0] if regions else "")
                    )
                    teecount = int(club.get("teecount") or 0)
                    price    = int(club.get("min_cost") or club.get("price") or 0)
                    code     = club.get("golfclub_code") or ""
                    seq      = club.get("golfclub_seq") or ""

                    if not name or teecount <= 0:
                        continue

                    booking_url = (
                        f"{self.BASE}/booking/{code}?roundDay={date}"
                        if code else f"{self.BASE}/home?roundDay={date}"
                    )
                    price_display = f"{teecount}개 가능"
                    if price:
                        price_display += f" (최저 {price:,}원)"

                    results.append({
                        "course_name": name,
                        "region": region,
                        "tee_time": "",     # 시간은 예약 페이지에서 확인
                        "price": price,
                        "price_display": price_display,
                        "available_slots": players,
                        "holes": 18,
                        "caddy_type": "",
                        "booking_url": booking_url,
                        "club_id": str(seq) if seq else None,
                    })

                if len(clubs) < page_size or (total_cnt and len(results) >= total_cnt):
                    break
                page += 1

            except Exception as e:
                logger.error(f"[티스캐너] page={page} 오류: {type(e).__name__}: {e}")
                break

        # 중복 제거 (동일 골프장명)
        seen: set = set()
        unique = []
        for r in results:
            if r["course_name"] not in seen:
                seen.add(r["course_name"])
                unique.append(r)

        logger.info(f"[티스캐너] 수집 완료: {len(unique)}개")
        return unique
