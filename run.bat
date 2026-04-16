@echo off
chcp 65001 >nul
echo ====================================
echo  골프 통합예약 검색 실행 중...
echo ====================================
echo.
echo  접속 주소: http://localhost:8000
echo  모바일:    http://[내 IP]:8000
echo  (종료: Ctrl+C)
echo.

cd /d "%~dp0backend"
python main.py
pause
