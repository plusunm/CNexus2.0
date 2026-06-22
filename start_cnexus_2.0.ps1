#!/usr/bin/env pwsh
<#
.SYNOPSIS
  CNexus 2.0 双子引擎点火脚本
.DESCRIPTION
  1. 启动 Pure Gateway (app_v2.py) → 端口 7864
  2. 启动 Next.js 观测面板 (原旧前端，已植入 ACL 防腐层) → 端口 3000
#>

Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "  🚀 CNexus 2.0 Twin-Engine Liftoff" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan

# 0. Kill any leftover on 7864
$existing = netstat -ano | Select-String ":7864.*LISTENING"
if ($existing) {
    Write-Host "  ⚠  Port 7864 in use — clearing..." -ForegroundColor Yellow
    $existing | ForEach-Object {
        $pid = $_ -replace '.*\s+(\d+)$', '$1'
        Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep 1
}

# 1. Start Pure Gateway (v2 backend)
$v2Dir = Split-Path -Parent $PSCommandPath
Write-Host "  🔥 Engine 1: Pure Gateway → 7864" -ForegroundColor Green
$v2Proc = Start-Process -FilePath python -ArgumentList "-B", "-u", (Join-Path $v2Dir "app_v2.py") -NoNewWindow -PassThru
Start-Sleep 2

# Verify 7864 is up
$check = netstat -ano | Select-String ":7864.*LISTENING"
if ($check) {
    Write-Host "  ✅ Engine 1: Gateway online (PID $($v2Proc.Id))" -ForegroundColor Green
} else {
    Write-Host "  ❌ Engine 1: Gateway failed to start" -ForegroundColor Red
    exit 1
}

# 2. Start Next.js frontend panel
$frontendDir = "D:\类脑记忆\CNexus — Observational Cognition Platform\brain-memory-ui\frontend"
if (-not (Test-Path $frontendDir)) {
    Write-Host "  ❌ Frontend dir not found: $frontendDir" -ForegroundColor Red
    exit 1
}

Write-Host "  🔥 Engine 2: Next.js Panel → 3000" -ForegroundColor Green
Set-Location $frontendDir
npm run dev

Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "  ✨ 双引擎已离地!"
Write-Host "     Panel: http://localhost:3000"
Write-Host "     Core:  http://127.0.0.1:7864/api/status"
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
