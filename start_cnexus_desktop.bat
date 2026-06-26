@echo off
setlocal EnableExtensions EnableDelayedExpansion

rem CNexus 2.0 desktop float launcher (ASCII-only for cmd.exe)
cd /d "%~dp0"
if errorlevel 1 (
    echo [ERROR] Cannot enter project directory.
    pause
    exit /b 1
)

title CNexus 2.0 Desktop

set "_PATH_ADD="
if exist "%ProgramFiles%\nodejs\" set "_PATH_ADD=%ProgramFiles%\nodejs;%_PATH_ADD%"
if exist "%ProgramFiles(x86)%\nodejs\" set "_PATH_ADD=%ProgramFiles(x86)%\nodejs;%_PATH_ADD%"
if exist "%LOCALAPPDATA%\Programs\nodejs\" set "_PATH_ADD=%LOCALAPPDATA%\Programs\nodejs;%_PATH_ADD%"
if exist "%USERPROFILE%\.cargo\bin\" set "_PATH_ADD=%USERPROFILE%\.cargo\bin;%_PATH_ADD%"
if defined _PATH_ADD set "PATH=%_PATH_ADD%%PATH%"

echo ========================================
echo   CNexus 2.0 - Floating Desktop
echo ========================================
echo.

set "DESKTOP_EXE=%~dp0frontend\src-tauri\target\release\cnexus-product.exe"
if not exist "!DESKTOP_EXE!" set "DESKTOP_EXE=%~dp0frontend\src-tauri\target\debug\cnexus-product.exe"

echo [1/3] Check gateway on port 7864...
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $r = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:7864/health' -TimeoutSec 2; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>&1
if not errorlevel 1 goto GW_READY

echo       Starting gateway...
if exist "%~dp0run_gateway_hidden.vbs" (
    wscript.exe //nologo "%~dp0run_gateway_hidden.vbs"
) else (
    start "" /B python "%~dp0app_v2.py"
)
set /a _GW=0
:WAIT_GW
ping -n 2 127.0.0.1 >nul
set /a _GW+=1
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $r = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:7864/health' -TimeoutSec 2; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>&1
if not errorlevel 1 goto GW_READY
if !_GW! lss 30 goto WAIT_GW
echo [WARN] Gateway slow to start; desktop may retry...

:GW_READY
echo       [OK] Gateway check done

if not exist "!DESKTOP_EXE!" goto DEV_MODE

echo [2/3] Launch desktop app...
echo       !DESKTOP_EXE!
echo.
echo Tips: tray icon or Alt+Shift+M toggles float bar. stop_cnexus.bat stops gateway.
echo.
start "" "!DESKTOP_EXE!"
ping -n 3 127.0.0.1 >nul
exit /b 0

:DEV_MODE
echo [2/3] Desktop exe not built - starting Tauri dev (first run 1-3 min)...
where node >nul 2>&1
if errorlevel 1 (
    echo.
    echo [ERROR] Node.js not found. Install from https://nodejs.org
    echo Or run:  powershell -ExecutionPolicy Bypass -File start_cnexus_desktop.ps1
    pause
    exit /b 1
)
where cargo >nul 2>&1
if errorlevel 1 (
    echo.
    echo [ERROR] Rust/Cargo not found. Install from https://rustup.rs
    pause
    exit /b 1
)

echo [3/3] Tauri dev - keep this window open. Ctrl+C to stop dev server.
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\dev-desktop.ps1" -Mode tauri
set EC=!ERRORLEVEL!
if not !EC!==0 pause
exit /b !EC!
