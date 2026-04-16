from abc import ABC, abstractmethod
from typing import List
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

DEBUG_DIR = Path(__file__).parent.parent / "debug"


class BaseScraper(ABC):
    name: str = ""
    enabled: bool = True

    @abstractmethod
    async def search(self, date: str, regions: List[str], players: int,
                     time_from: str, time_to: str) -> List[dict]:
        """
        Returns list of dicts:
          course_name, region, tee_time, price, price_display,
          available_slots, holes, caddy_type, booking_url
        """
        pass

    def _in_time_range(self, tee_time: str, time_from: str, time_to: str) -> bool:
        if not tee_time:
            return True  # 시간 미확인 → 항상 포함
        try:
            return time_from <= tee_time[:5] <= time_to
        except Exception:
            return True

    def _format_price(self, price: int) -> str:
        if not price:
            return "가격 미정"
        return f"{price:,}원"

    def _parse_price(self, raw: str) -> int:
        if not raw:
            return 0
        digits = "".join(c for c in raw if c.isdigit())
        # 가격이 너무 작으면(자리수 부족) 0 반환
        val = int(digits) if digits else 0
        return val if val >= 1000 else 0

    async def _screenshot(self, page, tag: str = ""):
        """디버그용 스크린샷 저장"""
        try:
            DEBUG_DIR.mkdir(exist_ok=True)
            path = str(DEBUG_DIR / f"{self.name}_{tag}.png")
            await page.screenshot(path=path, full_page=False)
            logger.info(f"[{self.name}] 스크린샷 저장 → debug/{self.name}_{tag}.png")
        except Exception as e:
            logger.debug(f"[{self.name}] 스크린샷 실패: {e}")

    async def _log_page_info(self, page):
        title = await page.title()
        logger.info(f"[{self.name}] 페이지: '{title}' | URL: {page.url}")

    async def _get_text(self, el, selectors: list) -> str:
        for sel in selectors:
            try:
                found = await el.query_selector(sel)
                if found:
                    text = await found.inner_text()
                    if text.strip():
                        return text.strip()
            except Exception:
                pass
        return ""

    async def _get_href(self, el, base_url: str) -> str:
        try:
            a = await el.query_selector("a")
            if a:
                href = await a.get_attribute("href")
                if href:
                    return href if href.startswith("http") else base_url.rstrip("/") + href
        except Exception:
            pass
        return base_url
