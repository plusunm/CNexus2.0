@echo off
setlocal EnableExtensions EnableDelayedExpansion

rem CNexus 2.0 launcher (ASCII-only for cmd.exe compatibility)
cd /d "%~dp0"
if errorlevel 1 (
    echo [ERROR] Cannot enter project directory.
    pause
    exit /b 1
)

title CNexus 2.0 Gateway

echo ========================================
echo   CNexus 2.0 - start backend + browser
echo ========================================

where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] python not found. Install Python 3.10+ and add to PATH.
    pause
    exit /b 1
)

echo [1/4] Check port 7864...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":7864" ^| findstr "LISTENING"') do (
    taskkill /f /pid %%a >nul 2>&1
)
ping -n 2 127.0.0.1 >nul

echo [2/4] Start gateway (hidden)...
if exist gateway.log del /f /q gateway.log >nul 2>&1
wscript.exe //nologo "%~dp0run_gateway_hidden.vbs"

echo [3/4] Wait for port...
set WAIT_MAX=30
set WAIT_COUNT=0

:WAIT_LOOP
ping -n 2 127.0.0.1 >nul
set /a WAIT_COUNT+=1
netstat -ano | findstr ":7864" | findstr "LISTENING" >nul 2>&1
if errorlevel 1 (
    if !WAIT_COUNT! lss !WAIT_MAX! goto WAIT_LOOP
    echo.
    echo [ERROR] Gateway did not start within !WAIT_MAX! seconds.
    if exist gateway.log (
        echo.
        echo --- gateway.log tail ---
        powershell -NoProfile -Command "Get-Content -LiteralPath '%CD%\gateway.log' -Tail 20 -ErrorAction SilentlyContinue"
    )
    echo.
    echo Try manually: cd /d "%~dp0" ^&^& python app_v2.py
    pause
    exit /b 1
)

echo [4/4] Health check...
set HEALTH_OK=0
for /l %%i in (1,1,10) do (
    powershell -NoProfile -Command "try { $r = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:7864/api/status' -TimeoutSec 3; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>&1
    if not errorlevel 1 (
        set HEALTH_OK=1
        goto HEALTH_DONE
    )
    ping -n 2 127.0.0.1 >nul
)
:HEALTH_DONE
if !HEALTH_OK! equ 0 (
    echo.
    echo [ERROR] Port is open but /api/status failed.
    if exist gateway.log (
        echo.
        echo --- gateway.log tail ---
        powershell -NoProfile -Command "Get-Content -LiteralPath '%CD%\gateway.log' -Tail 20 -ErrorAction SilentlyContinue"
    )
    pause
    exit /b 1
)

echo.
echo ========================================
echo   OK - CNexus is running
echo   UI:     http://127.0.0.1:7864
echo   Status: http://127.0.0.1:7864/api/status
echo   Log:    %CD%\gateway.log
echo   Stop:   run stop_cnexus.bat
echo ========================================

start "" http://127.0.0.1:7864

echo.
echo Gateway runs hidden in the background.
echo To stop: run stop_cnexus.bat
echo.
pause
exit /b 0
