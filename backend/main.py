import asyncio
import html as _html
import logging
import os
import sys
import requests as _requests
from pathlib import Path
from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from models import SearchRequest, SearchResponse, TeeTime
from scrapers import ALL_SCRAPERS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

app = FastAPI(title="골프 통합예약 검색", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"


def _run_scraper_sync(scraper, date, regions, players, time_from, time_to):
    """
    Playwright는 subprocess를 사용하므로 Windows uvicorn의 SelectorEventLoop와
    충돌합니다. 별도 스레드에서 ProactorEventLoop를 직접 생성해 실행합니다.
    """
    if sys.platform == "win32":
        loop = asyncio.ProactorEventLoop()
    else:
        loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(
            scraper.search(date=date, regions=regions, players=players,
                           time_from=time_from, time_to=time_to)
        )
    finally:
        loop.close()


_FOAPI_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://www.teescanner.com/",
    "Origin": "https://www.teescanner.com",
    "Accept": "application/json",
}


_KAKAO_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Origin": "https://www.kakao.golf",
    "Content-Type": "application/json",
    "Accept": "application/json",
}


_TEEUPNJOY_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
}


def _fetch_teeupnjoy_detail(club_id: str, date: str) -> list:
    date_fmt = date.replace("-", "")   # "20260425"
    headers = {**_TEEUPNJOY_HEADERS,
               "Referer": f"https://www.teeupnjoy.com/hp/clubid/{club_id}.do"}
    resp = _requests.post(
        "https://www.teeupnjoy.com/hp/join/hpJoinTeeTimeSearchClub.do",
        data=f"trgetTcYn=Y&bookingDay={date_fmt}&bookingEndDay={date_fmt}&clubId={club_id}&joinType=all",
        headers=headers, timeout=15,
    )
    resp.raise_for_status()
    raw = resp.json()
    items = (raw.get("resultList") or {}).get(date_fmt) or []
    seen_keys: set = set()
    result = []
    for t in items:
        book_time = t.get("bookingTime", "")
        if len(book_time) == 4:
            book_time = f"{book_time[:2]}:{book_time[2:]}"
        course = t.get("bookingCourse") or t.get("prName") or ""
        price_str = (t.get("bookDiscount") or "").replace(",", "").strip()
        price = int(price_str) if price_str.isdigit() else 0
        key = (book_time, course)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        result.append({
            "time":       book_time,
            "course":     course,
            "price":      price,
            "people":     0,
            "caddy":      t.get("regMemNo", ""),
            "discount":   False,
            "orig_price": price,
        })
    return result


def _fetch_kakao_detail(club_id: str, date: str) -> list:
    date_fmt = date.replace("-", "")   # "20260419"
    payload = {"golfInfoSeq": int(club_id), "date": date_fmt, "sigunguSeq": 0, "weekType": 0}
    headers = {**_KAKAO_HEADERS, "Referer": f"https://www.kakao.golf/golf/{club_id}"}
    resp = _requests.post("https://www.kakao.golf/api/golf/booktime",
                          json=payload, headers=headers, timeout=10)
    resp.raise_for_status()
    raw = resp.json()
    tee_times = raw.get("list") or []
    result = []
    for t in tee_times:
        book_time = t.get("bookTime", "")
        if len(book_time) == 4:
            book_time = f"{book_time[:2]}:{book_time[2:]}"
        price = int(t.get("greenFeeDC") or t.get("saleFee") or 0)
        orig = int(t.get("greenFeeDP") or price)
        result.append({
            "time":       book_time,
            "course":     t.get("CourseName", ""),
            "price":      price,
            "people":     int(t.get("visitorCnt") or 0),
            "caddy":      "",
            "discount":   t.get("cashbackYN") == "Y",
            "orig_price": orig,
        })
    return result


def _fetch_tscanner_detail(club_id: str, date: str) -> list:
    url = "https://foapi.teescanner.com/v1/booking/getTeeTimeListbyGolfclub"
    params = {"golfclub_seq": club_id, "roundDay": date, "orderType": ""}
    resp = _requests.get(url, params=params, headers=_FOAPI_HEADERS, timeout=10)
    resp.raise_for_status()
    raw = resp.json()
    tee_times = (raw.get("data") or {}).get("teeTimeList") or []
    return [
        {
            "time":   t.get("teetime_time", ""),
            "course": _html.unescape(t.get("course_name", "")),
            "price":  t.get("min_cost", 0),
            "people": t.get("round_people", 0),
            "caddy":  t.get("caddie_name", ""),
            "discount": t.get("discount_yn", "N") == "Y",
            "orig_price": t.get("min_orgin_cost", 0),
        }
        for t in tee_times
    ]


@app.get("/api/detail")
async def get_detail(platform: str = Query(...), club_id: str = Query(...), date: str = Query(...)):
    try:
        if platform == "티스캐너":
            slots = await asyncio.to_thread(_fetch_tscanner_detail, club_id, date)
            return {"slots": slots}
        elif platform == "카카오골프":
            slots = await asyncio.to_thread(_fetch_kakao_detail, club_id, date)
            return {"slots": slots}
        elif platform == "티업앤조이":
            slots = await asyncio.to_thread(_fetch_teeupnjoy_detail, club_id, date)
            return {"slots": slots}
        return {"slots": [], "message": "해당 플랫폼은 상세 조회를 지원하지 않습니다."}
    except Exception as e:
        logger.error(f"[detail] {platform} club_id={club_id}: {e}")
        return JSONResponse(status_code=500, content={"error": str(e), "slots": []})


@app.get("/api/platforms")
async def get_platforms():
    return [{"name": s.name, "enabled": s.enabled} for s in ALL_SCRAPERS]


@app.post("/api/search", response_model=SearchResponse)
async def search(req: SearchRequest):
    scrapers = [s for s in ALL_SCRAPERS if s.enabled]
    if req.platforms:
        scrapers = [s for s in scrapers if s.name in req.platforms]

    regions = [r for r in req.regions if r and r != "전체"]

    async def run_one(scraper):
        try:
            # 스레드 풀에서 실행 → 각 스크래퍼가 독립적인 ProactorEventLoop 사용
            items = await asyncio.to_thread(
                _run_scraper_sync, scraper,
                req.date, regions, req.players, req.time_from, req.time_to
            )
            return scraper.name, items, None
        except Exception as e:
            logger.error(f"[{scraper.name}] 실패: {type(e).__name__}: {e}")
            return scraper.name, [], str(e)

    raw = await asyncio.gather(*[run_one(s) for s in scrapers])

    all_results: list[TeeTime] = []
    errors = {}
    seen = set()

    for name, items, error in raw:
        if error:
            errors[name] = error
        for item in items:
            key = (name, item.get("course_name", ""), item.get("tee_time", ""))
            if key in seen:
                continue
            seen.add(key)
            all_results.append(TeeTime(platform=name, **item))

    all_results.sort(key=lambda x: x.tee_time if x.tee_time else "99:99")

    return SearchResponse(results=all_results, errors=errors, total=len(all_results))


# 로컬 개발 시에만 프론트엔드 정적 파일 서빙 (Vercel은 자체 CDN으로 서빙)
IS_VERCEL = bool(os.getenv("VERCEL"))

if not IS_VERCEL and FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        return FileResponse(str(FRONTEND_DIST / "index.html"))
elif not IS_VERCEL:
    @app.get("/")
    async def root():
        return {"message": "프론트엔드 빌드 필요"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
