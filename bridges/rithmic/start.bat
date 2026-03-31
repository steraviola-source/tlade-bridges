@echo off
title TLADe Bridge - Rithmic
echo.
echo   ========================================
echo    TLADe Bridge - Rithmic (R|Protocol)
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
    echo   Installing flask, flask-cors, async_rithmic...
    pip install flask flask-cors async_rithmic
    if %errorlevel% neq 0 (
        echo.
        echo   [!] pip install failed. Try manually:
        echo       pip install flask flask-cors async_rithmic
        echo.
        pause
        exit /b 1
    )
    echo.
) else (
    python -c "import async_rithmic" >nul 2>&1
    if %errorlevel% neq 0 (
        echo   Installing async_rithmic...
        pip install async_rithmic
    )
)
echo   [OK] Dependencies ready
echo.

:: ── Load saved config ──
set CONFIG_FILE=%~dp0.rithmic_config
if exist "%CONFIG_FILE%" (
    echo   [OK] Loading saved configuration...
    for /f "usebackq tokens=1,* delims==" %%a in ("%CONFIG_FILE%") do (
        set "%%a=%%b"
    )
    echo   User: %RITHMIC_USER%
    echo   System: %RITHMIC_SYSTEM%
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
echo   Supported systems:
echo     Apex, TopstepTrader, Bulenox, Earn2Trade,
echo     10XFutures, 4PropTrader, DayTraders.com,
echo     LegendsTrading, LucidTrading, MES Capital,
echo     PropShopTrader, TradeFundrr, Tradeify,
echo     ThriveTrading, Rithmic 01, Rithmic Paper Trading
echo.

set /p RITHMIC_USER="   Rithmic User ID: "
set /p RITHMIC_PASS="   Rithmic Password: "
set /p RITHMIC_SYSTEM="   System name (e.g. Apex): "

:: Optional: gateway
set RITHMIC_GATEWAY=wss://rithmic.com:443
set RITHMIC_GATEWAY_IP=34.254.173.171
echo.
set /p REGION="   Region - (E)urope or (U)S? [E]: "
if /i "%REGION%"=="U" (
    set RITHMIC_GATEWAY_IP=38.79.0.86
    echo   [OK] Using US gateway
) else (
    echo   [OK] Using Europe gateway
)

:: Save config
echo RITHMIC_USER=%RITHMIC_USER%> "%CONFIG_FILE%"
echo RITHMIC_PASS=%RITHMIC_PASS%>> "%CONFIG_FILE%"
echo RITHMIC_SYSTEM=%RITHMIC_SYSTEM%>> "%CONFIG_FILE%"
echo RITHMIC_GATEWAY=%RITHMIC_GATEWAY%>> "%CONFIG_FILE%"
echo RITHMIC_GATEWAY_IP=%RITHMIC_GATEWAY_IP%>> "%CONFIG_FILE%"
echo.
echo   [OK] Configuration saved to .rithmic_config
echo.

:LAUNCH
echo   ----------------------------------------
echo.
echo   IMPORTANT: Close RTrader Pro or NinjaTrader
echo   before starting (one market data session only).
echo.
echo   Starting bridge...
echo.
python "%~dp0tlade_bridge_rithmic.py"

pause
