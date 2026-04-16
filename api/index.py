import sys
import os

# backend/ 디렉터리를 Python 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from mangum import Mangum
from main import app  # noqa: E402

handler = Mangum(app, lifespan="off")
