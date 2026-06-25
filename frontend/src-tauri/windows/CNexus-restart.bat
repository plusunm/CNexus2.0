@echo off
:: Installed layout: copied to $INSTDIR alongside cnexus-product.exe
chcp 65001 >nul
title CNexus
set "INSTDIR=%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%INSTDIR%restart-cnexus-desktop.ps1" -ExePath "%INSTDIR%cnexus-product.exe" -TryStartOllama
set EC=%ERRORLEVEL%
if not %EC%==0 (
    echo.
    echo 若仍显示「未连接 Runtime」，请确认 Ollama 已运行后重试本脚本。
    pause
)
exit /b %EC%
