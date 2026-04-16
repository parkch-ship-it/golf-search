"""
티업앤조이 (teeupnjoy.com) — requests 기반 (Playwright 불필요)
- POST /hp/join/webMainList.do → HTML with .joinCnt[data-booking-day] 요소
- 각 행: th=코스명, td.joinCnt=날짜별 가능 수
- 예약 URL: /hp/clubid/{club_id}.do?bookingDay={YYYYMMDD}
"""
import re
import logging
import requests
from datetime import date as dt_date
from typing import List
from bs4 import BeautifulSoup
from .base import BaseScraper

logger = logging.getLogger(__name__)

# 지역 인덱스 → 표시 이름 (perArea div 순서 기준)
AREA_LABEL = {0: "경기북부", 1: "경기남부", 2: "강원", 3: "충청", 4: "경상", 5: "전라", 6: "제주"}

# 입력 지역 → perArea 인덱스 목록
REGION_TO_AREA = {
    "서울": [0],
    "경기": [0, 1],
    "인천": [1],
    "강원": [2],
    "충북": [3], "충남": [3], "대전": [3],
    "전북": [5], "전남": [5], "광주": [5],
    "경북": [4], "경남": [4], "대구": [4],
    "부산": [4], "울산": [4],
    "제주": [6],
}


class TeeUpNJoyScraper(BaseScraper):
    name = "티업앤조이"
    BASE = "https://www.teeupnjoy.com"

    async def search(self, date: str, regions: List[str], players: int,
                     time_from: str, time_to: str) -> List[dict]:

        today = dt_date.today()
        target = dt_date.fromisoformat(date)
        days_ahead = (target - today).days

        if days_ahead < 0 or days_ahead > 30:
            logger.warning(f"[티업앤조이] 날짜 범위 벗어남: {date}")
            return []

        date_fmt = date.replace("-", "")        # "20260425"
        today_fmt = today.strftime("%Y%m%d")    # "20260412"

        # 필요한 perArea 인덱스
        area_indices: set[int]
        if regions:
            area_indices = set()
            for r in regions:
                area_indices.update(REGION_TO_AREA.get(r, []))
        else:
            area_indices = set(range(7))

        results = []

        try:
            session = requests.Session()
            session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Referer": self.BASE + "/",
                "X-Requested-With": "XMLHttpRequest",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "Accept-Language": "ko-KR",
            })

            resp = session.post(
                f"{self.BASE}/hp/join/webMainList.do",
                data=f"dateFist={today_fmt}&dateLast={date_fmt}",
                timeout=20,
            )
            resp.encoding = "utf-8"
            soup = BeautifulSoup(resp.text, "html.parser")

            areas = soup.select(".perArea")
            logger.info(f"[티업앤조이] perArea 수: {len(areas)}, 대상 인덱스: {sorted(area_indices)}")

            for area_idx, area in enumerate(areas):
                if area_idx not in area_indices:
                    continue

                region_label = AREA_LABEL.get(area_idx, f"지역{area_idx}")

                # target date 의 .joinCnt 요소만 선택
                cells = area.select(f'.joinCnt[data-booking-day="{date_fmt}"]')
                logger.info(f"[티업앤조이] {region_label}: {date_fmt} joinCnt {len(cells)}개")

                for cell in cells:
                    cnt = int(cell.get("data-join-cnt", "0") or "0")
                    if cnt <= 0:
                        continue

                    club_id = cell.get("data-club-id", "")

                    # 코스명: 같은 행의 <th> 에서 추출
                    parent_tr = cell.find_parent("tr")
                    course_name = ""
                    if parent_tr:
                        th = parent_tr.select_one("th")
                        if th:
                            # <p class="name">코스명</p> 전용 요소 사용
                            name_el = th.select_one("p.name")
                            if name_el:
                                course_name = name_el.get_text(strip=True)
                            else:
                                # fallback: 전체 텍스트에서 괄호 제거
                                raw = th.get_text(strip=True)
                                course_name = re.sub(r'\([^)]*\)', '', raw).strip()

                    if not course_name:
                        course_name = f"골프장 #{club_id}"

                    booking_url = (
                        f"{self.BASE}/hp/clubid/{club_id}.do?bookingDay={date_fmt}"
                        if club_id else self.BASE
                    )

                    results.append({
                        "course_name": course_name,
                        "region": region_label,
                        "tee_time": "",             # 실제 시간은 예약 페이지에서 확인
                        "price": 0,
                        "price_display": f"{cnt}개 가능",
                        "available_slots": players,
                        "holes": 18,
                        "caddy_type": "",
                        "booking_url": booking_url,
                        "club_id": club_id if club_id else None,
                    })

        except Exception as e:
            logger.error(f"[티업앤조이] 오류: {type(e).__name__}: {e}")

        # 중복 제거 (같은 코스명)
        seen: set[str] = set()
        unique = []
        for r in results:
            if r["course_name"] not in seen:
                seen.add(r["course_name"])
                unique.append(r)

        logger.info(f"[티업앤조이] 수집 완료: {len(unique)}개")
        return unique
