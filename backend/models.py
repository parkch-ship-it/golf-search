from pydantic import BaseModel
from typing import Optional, List


class SearchRequest(BaseModel):
    date: str                              # YYYY-MM-DD
    regions: List[str] = []               # 빈 리스트 = 전체
    players: int = 4
    time_from: str = "06:00"
    time_to: str = "18:00"
    platforms: Optional[List[str]] = None # None = 전체


class TeeTime(BaseModel):
    platform: str
    course_name: str
    region: str = ""
    tee_time: str                          # HH:MM
    price: Optional[int] = None
    price_display: str = ""
    available_slots: int = 4
    holes: int = 18
    caddy_type: str = ""
    booking_url: str
    source_url: str = ""
    club_id: Optional[str] = None          # 상세 조회용 클럽 ID (플랫폼별)


class SearchResponse(BaseModel):
    results: List[TeeTime]
    errors: dict = {}
    total: int = 0
