# CNexus 2.0 - launch floating desktop (PowerShell; reliable on Unicode paths)
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $RepoRoot

function Test-Gateway {
    foreach ($path in @("/health", "/api/status")) {
        try {
            $r = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:7864$path" -TimeoutSec 2
            if ($r.StatusCode -eq 200) { return $true }
        } catch { }
    }
    return $false
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  CNexus 2.0 - Floating Desktop" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Gateway)) {
    Write-Host "[1/2] Starting gateway on :7864..." -ForegroundColor Gray
    $vbs = Join-Path $RepoRoot "run_gateway_hidden.vbs"
    if (Test-Path $vbs) {
        wscript.exe //nologo $vbs
    } else {
        Start-Process -FilePath "python" -ArgumentList (Join-Path $RepoRoot "app_v2.py") -WindowStyle Hidden
    }
    $ready = $false
    for ($i = 0; $i -lt 40; $i++) {
        if (Test-Gateway) { $ready = $true; break }
        Start-Sleep -Milliseconds 500
    }
    if ($ready) { Write-Host "      [OK] Gateway ready" -ForegroundColor Green }
    else { Write-Host "      [WARN] Gateway slow — desktop may retry" -ForegroundColor Yellow }
} else {
    Write-Host "[1/2] [OK] Gateway already on :7864" -ForegroundColor Green
}

$releaseExe = Join-Path $RepoRoot "frontend\src-tauri\target\release\cnexus-product.exe"
$debugExe = Join-Path $RepoRoot "frontend\src-tauri\target\debug\cnexus-product.exe"
$desktopExe = if (Test-Path $releaseExe) { $releaseExe } elseif (Test-Path $debugExe) { $debugExe } else { $null }

if ($desktopExe) {
    Write-Host "[2/2] Launching desktop app..." -ForegroundColor Green
    Write-Host "      $desktopExe" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Tips: system tray CNexus icon, or Alt+Shift+M to toggle float bar." -ForegroundColor Gray
    Start-Process -FilePath $desktopExe -WorkingDirectory (Split-Path $desktopExe -Parent)
    exit 0
}

Write-Host "[2/2] Desktop exe not built — starting Tauri dev..." -ForegroundColor Yellow
& (Join-Path $RepoRoot "scripts\dev-desktop.ps1") -Mode tauri
