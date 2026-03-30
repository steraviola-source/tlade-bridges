@echo off
title TLADe Bridge - Interactive Brokers
echo.
echo   ========================================
echo    TLADe Bridge Lite - Interactive Brokers
echo   ========================================
echo.

:: ── Check Python ──
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo   [!] Python not found.
    echo.
    echo   TLADe Bridge requires Python 3.8 or later.
    echo   Opening the download page...
    echo.
    start https://www.python.org/downloads/
    echo   After installing Python:
    echo     - Check "Add Python to PATH" during install
    echo     - Restart this script
    echo.
    pause
    exit /b 1
)

for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo   [OK] Python %PYVER% found
echo.

:: ── Check/install dependencies ──
echo   Checking dependencies...
python -c "import flask" >nul 2>&1
if %errorlevel% neq 0 (
    echo   Installing flask, flask-cors, ib_insync...
    pip install flask flask-cors ib_insync
    if %errorlevel% neq 0 (
        echo.
        echo   [!] pip install failed. Try manually:
        echo       pip install flask flask-cors ib_insync
        echo.
        pause
        exit /b 1
    )
    echo.
) else (
    python -c "import ib_insync" >nul 2>&1
    if %errorlevel% neq 0 (
        echo   Installing ib_insync...
        pip install ib_insync
    )
)
echo   [OK] Dependencies ready
echo.

:: ── Launch bridge ──
echo   Starting bridge...
echo   Make sure TWS or IB Gateway is running with API enabled on port 7496
echo.
echo   ----------------------------------------
echo.
python "%~dp0tlade_bridge_lite.py"

pause
