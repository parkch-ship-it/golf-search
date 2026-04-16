from .tscanner import TScannerScraper
from .kakao_golf import KakaoGolfScraper
from .teeupnjoy import TeeUpNJoyScraper
from .smartscore import SmartScoreScraper
from .golfzon import GolfzonScraper

ALL_SCRAPERS = [
    TScannerScraper(),
    KakaoGolfScraper(),
    TeeUpNJoyScraper(),
    SmartScoreScraper(),
    GolfzonScraper(),
]

SCRAPER_MAP = {s.name: s for s in ALL_SCRAPERS}
