@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [HATA] Sanal ortam ^(.venv^) bulunamadi!
    pause
    exit /b 1
)

call ".venv\Scripts\activate.bat"
python "pc-server\main.py"
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
    echo.
    echo [HATA] Uygulama %EXIT_CODE% kodu ile kapandi.
    pause
)

exit /b %EXIT_CODE%
