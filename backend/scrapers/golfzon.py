"""
골프존카운티 (golfzoncounty.com)
- 날짜 클릭 시 로그인 필요 → enabled=False로 비활성화
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


class GolfzonScraper(BaseScraper):
    name = "골프존카운티"
    enabled = False  # 날짜 클릭 시 로그인 모달 → 비로그인 스크래핑 불가
    BASE = "https://www.golfzoncounty.com"

    async def search(self, date: str, regions: List[str], players: int,
                     time_from: str, time_to: str) -> List[dict]:
        logger.info("[골프존카운티] 로그인 필요 - 건너뜀")
        return []

    async def _search_impl(self, date: str, regions, players, time_from, time_to):
        results = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800},
                ignore_https_errors=True,
                locale="ko-KR",
            )
            page = await context.new_page()

            try:
                await page.goto(f"{self.BASE}/reserve/main", wait_until="domcontentloaded", timeout=30000)
                await self._log_page_info(page)
                await self._screenshot(page, "01_home")

                # 팝업 닫기 (여러 패턴 시도)
                await self._close_popups(page)
                await self._screenshot(page, "02_no_popup")

                # 타겟 날짜 클릭
                day = date[8:].lstrip("0")  # "25"
                clicked = False
                for sel in [
                    f"button:has-text('{day}')",
                    f"td:has-text('{day}')",
                    f"span:has-text('{day}')",
                    f"a:has-text('{day}')",
                    f"[class*='day']:has-text('{day}')",
                ]:
                    try:
                        await page.click(sel, timeout=3000)
                        await page.wait_for_load_state("domcontentloaded", timeout=8000)
                        clicked = True
                        logger.info(f"[골프존카운티] 날짜 '{day}' 클릭 성공")
                        break
                    except Exception:
                        pass

                if not clicked:
                    logger.warning(f"[골프존카운티] 날짜 '{day}' 클릭 실패")

                await self._screenshot(page, "03_date_selected")

                # 지역 필터
                if regions:
                    region_name = regions[0]
                    for sel in [f"text={region_name}", f"button:has-text('{region_name}')"]:
                        try:
                            await page.click(sel, timeout=3000)
                            await page.wait_for_load_state("domcontentloaded")
                            break
                        except Exception:
                            pass

                # 결과 대기
                try:
                    await page.wait_for_selector(
                        "[class*='teeTime'], [class*='TeeTime'], .tee-time, table tbody tr",
                        timeout=10000
                    )
                except PWTimeout:
                    pass

                await self._screenshot(page, "04_results")

                # 결과 파싱
                item_sels = [
                    "[class*='teeTimeItem']", "[class*='TeeTimeItem']",
                    "[class*='bookingItem']", ".tee-time-item",
                    "table tbody tr",
                ]
                items = []
                for sel in item_sels:
                    items = await page.query_selector_all(sel)
                    if items:
                        logger.info(f"[골프존카운티] 셀렉터 '{sel}' → {len(items)}개")
                        break

                for item in items:
                    try:
                        course = await self._get_text(item, [
                            "[class*='courseName']", "[class*='name']",
                            "strong", "h3", "td:first-child",
                        ])
                        tee_time_raw = await self._get_text(item, [
                            "[class*='time']", ".time", "time",
                        ])
                        price_raw = await self._get_text(item, [
                            "[class*='price']", "[class*='fee']",
                        ])
                        href = await self._get_href(item, self.BASE)

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
                        logger.debug(f"[골프존카운티] 파싱 오류: {e}")

            except Exception as e:
                logger.error(f"[골프존카운티] 오류: {type(e).__name__}: {e}")
                await self._screenshot(page, "error")
            finally:
                await browser.close()

        logger.info(f"[골프존카운티] 수집 완료: {len(results)}개")
        return results

    async def _close_popups(self, page):
        """팝업/모달 닫기"""
        # 팝업 로딩 대기
        try:
            await page.wait_for_selector(".layer_popup_container", timeout=3000)
        except Exception:
            pass

        close_sels = [
            # 골프존카운티 layer_popup: 하단 버튼 구조
            ".layer_popup_bottom button",           # 하단 버튼 (닫기)
            ".layer_popup_bottom button:last-child",
            "button[onclick*='closeLayer']",
            "button[onclick*='close']",
            # 일반 닫기 패턴
            "button:has-text('닫기')",
            "a:has-text('닫기')",
            "button:has-text('나중에')", "a:has-text('나중에')",
            "[class*='close']", "[class*='Close']",
            ".modal-close", ".popup-close",
            "[aria-label='close']",
        ]
        for attempt in range(5):
            closed = False
            for sel in close_sels:
                try:
                    await page.click(sel, timeout=2000)
                    logger.info(f"[골프존카운티] 팝업 닫기 (시도 {attempt+1}): {sel}")
                    await page.wait_for_timeout(800)
                    closed = True
                    break
                except Exception:
                    pass
            if not closed:
                break

        try:
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(300)
        except Exception:
            pass
