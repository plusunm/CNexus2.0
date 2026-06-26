@echo off
setlocal EnableExtensions

if "%~1"=="quiet" goto :do_kill

echo.
echo ========================================
echo   CNexus - stop processes before build
echo ========================================
echo.

:do_kill
set "SCRIPT_DIR=%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%kill-cnexus-runtime.ps1" >nul 2>&1
powershell -NoProfile -Command "Start-Sleep -Seconds 2"

if "%~1"=="quiet" exit /b 0

echo.
echo [OK] Processes cleared
echo.
endlocal
