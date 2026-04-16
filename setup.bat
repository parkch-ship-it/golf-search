@echo off
chcp 65001 >nul
echo ====================================
echo  골프 통합예약 검색 - 초기 설치
echo ====================================
echo.

:: Python 패키지 설치
echo [1/4] Python 패키지 설치 중...
cd /d "%~dp0backend"
pip install -r requirements.txt
if errorlevel 1 ( echo [오류] Python 패키지 설치 실패 & pause & exit /b 1 )

:: Playwright 브라우저 설치
echo.
echo [2/4] Playwright Chromium 브라우저 설치 중...
python -m playwright install chromium
if errorlevel 1 ( echo [오류] Playwright 설치 실패 & pause & exit /b 1 )

:: Node.js 패키지 설치
echo.
echo [3/4] Node.js 패키지 설치 중...
cd /d "%~dp0frontend"
npm install
if errorlevel 1 ( echo [오류] npm install 실패 & pause & exit /b 1 )

:: 프론트엔드 빌드
echo.
echo [4/4] 프론트엔드 빌드 중...
npm run build
if errorlevel 1 ( echo [오류] 빌드 실패 & pause & exit /b 1 )

echo.
echo ====================================
echo  설치 완료! run.bat 으로 실행하세요
echo ====================================
pause
