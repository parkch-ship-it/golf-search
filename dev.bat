@echo off
chcp 65001 >nul
echo ====================================
echo  개발 모드 실행 (핫 리로드)
echo ====================================
echo.
echo  백엔드: http://localhost:8000
echo  프론트: http://localhost:5173
echo.

:: 백엔드 백그라운드 실행
start "골프검색-백엔드" cmd /k "cd /d "%~dp0backend" && python main.py"

:: 잠시 대기 후 프론트엔드 실행
timeout /t 2 >nul
start "골프검색-프론트엔드" cmd /k "cd /d "%~dp0frontend" && npm run dev"

echo 두 창이 열렸습니다.
echo 브라우저에서 http://localhost:5173 로 접속하세요.
pause
