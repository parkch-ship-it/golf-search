"""
스마트스코어 (smartscore.co.kr)
SSL 오류 → ignore_https_errors + http 시도
"""
import re
import logging
from typing import List
from .base import BaseScraper

try:
    from playwright.async_api import async_playwright, TimeoutError as PWTimeout
    _HAS_PLAYWRIGHT = True
except ImportError:
    _HAS_PLAYWRIGHT = False

logger = logging.getLogger(__name__)

CANDIDATE_URLS = [
    "https://smartscore.co.kr",
    "http://www.smartscore.co.kr",
    "https://www.smartscore.co.kr",
    "https://m.smartscore.co.kr",
]


class SmartScoreScraper(BaseScraper):
    name = "스마트스코어"

    async def search(self, date: str, regions: List[str], players: int,
                     time_from: str, time_to: str) -> List[dict]:
        if not _HAS_PLAYWRIGHT:
            logger.info("[스마트스코어] Playwright 미설치 - 건너뜀")
            return []
        results = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--ignore-certificate-errors"],
            )
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                viewport={"width": 1440, "height": 900},
                ignore_https_errors=True,
                locale="ko-KR",
            )
            page = await context.new_page()

            # 접속 가능한 URL 탐색
            base_url = None
            for url in CANDIDATE_URLS:
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                    title = await page.title()
                    logger.info(f"[스마트스코어] {url} → '{title}'")
                    if title and len(title) > 1:
                        base_url = url
                        break
                except Exception as e:
                    logger.debug(f"[스마트스코어] {url} 실패: {e}")
                    continue

            if not base_url:
                logger.error("[스마트스코어] 접속 가능한 도메인 없음")
                await browser.close()
                return []

            await self._screenshot(page, "01_home")

            try:
                search_paths = [
                    f"/booking/list?date={date}&count={players}",
                    f"/booking?rsvDate={date}",
                    f"/greenfee/list?date={date}",
                    "/booking",
                ]
                for path in search_paths:
                    try:
                        url = base_url + path
                        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                        logger.info(f"[스마트스코어] {url} → '{await page.title()}'")
                        items = await page.query_selector_all(
                            ".booking-list li, [class*='booking'], [class*='course']"
                        )
                        if items:
                            break
                    except PWTimeout:
                        continue

                await self._screenshot(page, "02_results")

                item_sels = [
                    ".booking-list li", "[class*='bookingItem']",
                    "[class*='courseItem']", "[class*='BookingItem']",
                    "table tbody tr", ".item", "li[class*='item']",
                ]
                items = []
                for sel in item_sels:
                    items = await page.query_selector_all(sel)
                    if len(items) > 1:
                        logger.info(f"[스마트스코어] 셀렉터 '{sel}' → {len(items)}개")
                        break

                for item in items:
                    try:
                        course = await self._get_text(item, [
                            "[class*='courseName']", "[class*='name']", "strong", "h3", "td:first-child"
                        ])
                        tee_time_raw = await self._get_text(item, [
                            "[class*='teeTime']", "[class*='time']", "time"
                        ])
                        price_raw = await self._get_text(item, [
                            "[class*='price']", "[class*='fee']"
                        ])
                        href = await self._get_href(item, base_url)

                        if not course or not tee_time_raw:
                            continue
                        m = re.search(r'(\d{1,2}):(\d{2})', tee_time_raw)
                        if not m:
                            continue
                        t = f"{int(m.group(1)):02d}:{m.group(2)}"
                        if not self._in_time_range(t, time_from, time_to):
                            continue

                        price = self._parse_price(price_raw)
                        results.append({
                            "course_name": course,
                            "region": regions[0] if regions else "",
                            "tee_time": t, "price": price,
                            "price_display": self._format_price(price),
                            "available_slots": players, "holes": 18,
                            "caddy_type": "", "booking_url": href,
                        })
                    except Exception as e:
                        logger.debug(f"[스마트스코어] 파싱 오류: {e}")

            except Exception as e:
                logger.error(f"[스마트스코어] 오류: {type(e).__name__}: {e}")
                await self._screenshot(page, "error")
            finally:
                await browser.close()

        logger.info(f"[스마트스코어] 수집 완료: {len(results)}개")
        return results
