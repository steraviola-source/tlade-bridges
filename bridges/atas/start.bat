@echo off
:: SPDX-License-Identifier: MIT
:: Copyright (c) 2026 Mihai Ostafe — TLADe ATAS Bridge contribution
:: Copyright (c) 2026 TLADe — Trade Like a Dealer (https://tradelikeadealer.com)
title TLADe Bridge - ATAS
echo.
echo   =====================================
echo    TLADe Bridge - ATAS Edition v1.2.0
echo   =====================================
echo.
echo   Architecture:
echo     ATAS (Rithmic/CQG)
echo       -^> TLAdeBridgeATAS.cs (ATAS indicator, HTTP push)
echo             -^> tlade_bridge_atas.py (receiver, localhost:5000)
echo                   -^> TLADe Terminal (auto-detects on localhost:5000)
echo.

:: ── Check Python ──
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo   [!] Python not found.
    echo.
    echo   TLADe Bridge requires Python 3.8 or newer.
    echo   Download from: https://www.python.org/downloads/
    echo   Tick "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo   [OK] Python %PYVER% found
echo.

:: ── Check/install dependencies ──
echo   Checking dependencies (flask, flask-cors)...
python -c "import flask, flask_cors" >nul 2>&1
if %errorlevel% neq 0 (
    echo   Installing flask flask-cors...
    pip install flask flask-cors >nul 2>&1
    echo.
    :: Re-verify the import after install — this is the real success check
    python -c "import flask, flask_cors" >nul 2>&1
    if %errorlevel% neq 0 (
        echo   [!] flask/flask-cors cannot be imported after install.
        echo.
        echo   Try manually in a Command Prompt:
        echo       pip install flask flask-cors
        echo   then verify:
        echo       python -c "import flask, flask_cors"
        echo.
        pause
        exit /b 1
    )
)
echo   [OK] Dependencies OK
echo.

:: ── Check whether port 5000 is already LISTENING ──
netstat -ano | findstr "LISTENING" | findstr ":5000 " >nul 2>&1
if %errorlevel% equ 0 (
    echo   [!] Port 5000 is already in use by another process.
    echo       Inspect with: netstat -ano ^| findstr :5000
    echo       Stop the process using port 5000 and relaunch.
    echo.
    pause
    exit /b 1
)

:: ── Launch ──
echo   Starting TLADe ATAS Bridge...
echo   Waiting for data from the TLAdeBridgeATAS indicator in ATAS...
echo.
echo   (Leave this window open while you trade)
echo.
python "%~dp0tlade_bridge_atas.py"

echo.
echo   Bridge stopped.
pause
