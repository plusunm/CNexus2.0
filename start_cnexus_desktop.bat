@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title CNexus 2.0 Desktop

echo ========================================
echo   CNexus 2.0 - Floating Desktop
echo ========================================
echo.

where node >nul 2>&1
if errorlevel 1 (
    echo [ERROR] node not found. Install Node.js 20+.
    pause
    exit /b 1
)

where cargo >nul 2>&1
if errorlevel 1 (
    echo [WARN] Rust/Cargo not found. Install from https://rustup.rs
    echo        Required for Tauri float window.
    pause
    exit /b 1
)

echo.
echo Starting Tauri float window (first run may compile 1-3 min)...
echo Keep this window open. Close with Ctrl+C when done.
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\dev-desktop.ps1" -Mode tauri
set EC=%ERRORLEVEL%
if not %EC%==0 pause
exit /b %EC%
