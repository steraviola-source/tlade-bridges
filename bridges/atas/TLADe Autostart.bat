@echo off
title TLADe Autostart
rem Launches the TLADe ATAS bridge + the live GEX auto-fetch at Windows logon.
set "TLDIR=D:\Automatizare Atas\tlade-bridges-main\tlade-bridges-main\bridges\atas"

rem --- Start the bridge only if port 5000 is not already listening ---
netstat -ano | findstr "LISTENING" | findstr ":5000 " >nul 2>&1
if errorlevel 1 (
    echo Starting TLADe bridge...
    start "TLADe Bridge" /d "%TLDIR%" cmd /k python tlade_bridge_atas.py
) else (
    echo Bridge already running on port 5000.
)

rem --- Give the bridge a moment to bind the port ---
timeout /t 8 /nobreak >nul

rem --- Start the live GEX auto-fetch (scrapes Zero Gamma, pushes to the bridge) ---
echo Starting TLADe auto-fetch...
start "TLADe AutoFetch" /d "%TLDIR%" cmd /k python tlade_auto_fetch.py

exit
