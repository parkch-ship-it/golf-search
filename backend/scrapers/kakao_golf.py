"""
카카오골프 (kakao.golf) — requests 기반
- POST https://www.kakao.golf/api/golf/info/list     → 골프장 이름 목록 (캐시)
- POST https://www.kakao.golf/api/tee-time/search    → 날짜별 티타임 검색
"""
import logging
import requests
from typing import List, Optional
from .base import BaseScraper

logger = logging.getLogger(__name__)

BASE = "https://www.kakao.golf"

# areas1s 실제 API 코드 (POST /api/location/area 의 code=1 seq 값)
REGION_TO_AREAS1 = {
    "서울": 1, "경기": 1, "인천": 1,
    "강원": 12,
    "충북": 22, "충남": 22, "대전": 22, "세종": 22,
    "경북": 31, "경남": 31, "대구": 31, "부산": 31, "울산": 31,
    "전북": 41, "전남": 41, "광주": 41,
    "제주": 46,
}
AREAS1_LABEL = {1: "서울/경기", 12: "강원", 22: "충청", 31: "경상", 41: "전라", 46: "제주"}
ALL_AREAS1 = [1, 12, 22, 31, 41, 46]

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": f"{BASE}/tee-time",
    "Origin": BASE,
    "Content-Type": "application/json",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ko-KR,ko;q=0.9",
}

_FILTER_DEFAULT = {
    "greenFee": 0, "greenFeeList": [],
    "timeZone": 0, "timeZoneList": [0],
    "orderForGolfClubListMode": 0, "orderForTeeTimeListMode": 0,
    "timeZoneDisable": 0, "greenFeeDisable": 0,
    "paymentMethodDisable": 0, "visitorCntDisable": 0,
    "eventEnable": False, "paymentMethodFlag": 0, "paymentMethodList": [],
    "visitorCntFlag": 0, "visitorCnts": [],
    "holeCnt": 0, "holeCntFlag": 0, "holeCntList": [],
    "event": 0, "events": [],
    "isOnlyAvailableTeeTime": False,
    "isOnlyCashBackTeeTime": False,
    "isOnlyLowGuarantee": False,
    "paymentMethod": "", "visitorCnt": 0,
}


class KakaoGolfScraper(BaseScraper):
    name = "카카오골프"
    BASE = BASE

    # golfInfoSeq → {name, area1, area2} 캐시
    _golf_info: Optional[dict] = None

    # ─── 골프장 정보 캐시 ──────────────────────────────────────

    def _load_golf_info(self):
        self._golf_info = {}
        try:
            resp = requests.post(
                f"{BASE}/api/golf/info/list",
                json={"appVersion": "1"},
                headers=_HEADERS, timeout=15,
            )
            clubs = resp.json().get("list", [])
            for club in clubs:
                seq = club.get("golfInfoSeq")
                if seq:
                    self._golf_info[seq] = {
                        "name":  club.get("golfInfoName", ""),
                        "area1": club.get("area1", ""),
                        "area2": club.get("area2", ""),
                    }
            logger.info(f"[카카오골프] 골프장 캐시: {len(self._golf_info)}개")
        except Exception as e:
            logger.error(f"[카카오골프] 골프장 목록 로드 실패: {type(e).__name__}: {e}")
            self._golf_info = {}

    # ─── 검색 ───────────────────────────────────────────────────

    async def search(self, date: str, regions: List[str], players: int,
                     time_from: str, time_to: str) -> List[dict]:
        if self._golf_info is None:
            self._load_golf_info()

        date_fmt = date.replace("-", "")    # "20260425"

        # regions → areas1s 코드
        if regions:
            areas_set = {REGION_TO_AREAS1[r] for r in regions if r in REGION_TO_AREAS1}
            areas1s = list(areas_set) if areas_set else ALL_AREAS1
        else:
            areas1s = list(range(1, 7))

        session = requests.Session()
        session.headers.update(_HEADERS)

        results = []

        for area_id in areas1s:
            area_label = AREAS1_LABEL.get(area_id, f"지역{area_id}")
            try:
                payload = {
                    "date": date_fmt,
                    "qfSeq": "0",
                    "searchType": 2,
                    "lowGuarantee": "N",
                    "selectedDates": None,
                    "flagCashBack": "N",
                    "quickFilterTypeHistory": None,
                    "weekType": "1",
                    "areas1s": [area_id],
                    "enterType": "MAIN_AREA",
                    "searchSeq": str(area_id),
                    "reservFlag": "N",
                    "title": area_label,
                    "listType": "0",
                    "detailAreaText": "",
                    "filter": _FILTER_DEFAULT,
                    "isOnlyCashBackCondition": "false",
                    "golfinfos": [],
                    "searchName": area_label,
                    "areas2": [0],
                    "sigunguSeq": "459",
                }

                resp = session.post(
                    f"{BASE}/api/tee-time/search",
                    json=payload, timeout=20,
                )
                items = resp.json().get("list", [])
                logger.info(f"[카카오골프] area={area_id}({area_label}): {len(items)}개")

                for item in items:
                    golf_seq = item.get("golfInfoSeq")
                    time_cnt = int(item.get("timeCnt") or item.get("totalTime") or 0)
                    price    = int(item.get("minGreenFeeNO") or 0)

                    if time_cnt <= 0:
                        continue

                    club_info = self._golf_info.get(golf_seq, {})
                    name = club_info.get("name") or f"골프장 #{golf_seq}"
                    region = club_info.get("area1") or area_label

                    booking_url = (
                        f"{BASE}/golf/{golf_seq}?date={date_fmt}"
                        if golf_seq else BASE
                    )
                    price_display = f"{time_cnt}개 가능"
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
                        "club_id": str(golf_seq) if golf_seq else None,
                    })

            except Exception as e:
                logger.error(f"[카카오골프] area={area_id} 오류: {type(e).__name__}: {e}")

        # 중복 제거
        seen: set = set()
        unique = []
        for r in results:
            if r["course_name"] not in seen:
                seen.add(r["course_name"])
                unique.append(r)

        logger.info(f"[카카오골프] 수집 완료: {len(unique)}개")
        return unique
