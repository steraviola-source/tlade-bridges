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

:: ── Load saved config ──
set CONFIG_FILE=%~dp0.ib_config
if exist "%CONFIG_FILE%" (
    echo   [OK] Loading saved configuration...
    for /f "usebackq tokens=1,* delims==" %%a in ("%CONFIG_FILE%") do (
        set "%%a=%%b"
    )
    echo   TWS Host: %IB_HOST%
    echo   TWS Port: %IB_PORT%
    echo   Client ID: %IB_CLIENT%
    echo.
    set /p REUSE="   Use these settings? (Y/n): "
    if /i "%REUSE%"=="n" goto :SETUP
    goto :LAUNCH
)

:SETUP
echo.
echo   ----------------------------------------
echo   First-time setup
echo   ----------------------------------------
echo.
echo   Make sure TWS or IB Gateway is running
echo   with API enabled (File ^> Global Configuration
echo   ^> API ^> Settings ^> Enable Socket Clients)
echo.

set IB_HOST=127.0.0.1
set /p IB_PORT="   TWS API port (7496=live, 7497=paper) [7496]: "
if "%IB_PORT%"=="" set IB_PORT=7496
set /p IB_CLIENT="   Client ID (change if other apps use TWS) [10]: "
if "%IB_CLIENT%"=="" set IB_CLIENT=10

:: Save config
echo IB_HOST=%IB_HOST%> "%CONFIG_FILE%"
echo IB_PORT=%IB_PORT%>> "%CONFIG_FILE%"
echo IB_CLIENT=%IB_CLIENT%>> "%CONFIG_FILE%"
echo.
echo   [OK] Configuration saved to .ib_config
echo.

:LAUNCH
echo   ----------------------------------------
echo.
echo   Starting bridge (TWS %IB_HOST%:%IB_PORT%)...
echo.
python "%~dp0tlade_bridge_lite.py"

pause
