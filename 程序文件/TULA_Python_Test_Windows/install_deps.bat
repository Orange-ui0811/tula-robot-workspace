@echo off
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"

echo ================================================
echo Install TULA Python dependencies
echo ================================================
echo.

where python >nul 2>nul
if %errorlevel%==0 (
    python -m pip install -r requirements.txt
) else (
    py -m pip install -r requirements.txt
)

echo.
echo If you see "Successfully installed" or "Requirement already satisfied", installation is complete.
pause
