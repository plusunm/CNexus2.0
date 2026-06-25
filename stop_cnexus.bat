@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo Stopping CNexus gateway on port 7864...
set FOUND=0
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":7864" ^| findstr "LISTENING"') do (
    set FOUND=1
    taskkill /f /pid %%a >nul 2>&1
    if errorlevel 1 (
        echo [WARN] Could not stop PID %%a
    ) else (
        echo [OK] Stopped PID %%a
    )
)

if "%FOUND%"=="0" (
    echo No gateway process found on port 7864.
) else (
    echo Gateway stopped.
)

pause
exit /b 0
