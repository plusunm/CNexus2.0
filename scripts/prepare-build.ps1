# CNexus Personal Edition — prepare repo for web gateway build (所筑即所测)
param(
    [switch]$SkipTests,
    [switch]$SkipFrontend,
    [switch]$Desktop
)

$ErrorActionPreference = "Stop"
$ScriptDir = $PSScriptRoot
$Root = Split-Path -Parent $ScriptDir
$Frontend = Join-Path $Root "frontend"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " CNexus prepare-build (Personal Edition)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Push-Location $Root
try {
    Write-Host "[1/5] Clean local build artifacts..." -ForegroundColor Gray
    git restore frontend/tsconfig.tsbuildinfo 2>$null
    if (Test-Path "frontend/tsconfig.tsbuildinfo") {
        Remove-Item "frontend/tsconfig.tsbuildinfo" -Force -ErrorAction SilentlyContinue
    }

    Write-Host "[2/5] Python deps..." -ForegroundColor Gray
    python -m pip install -q -r requirements.txt

    if (-not $SkipTests) {
        Write-Host "[3/5] pytest..." -ForegroundColor Gray
        python -m pytest tests/ -q
        if ($LASTEXITCODE -ne 0) { throw "pytest failed" }
    } else {
        Write-Host "[3/5] pytest skipped" -ForegroundColor Yellow
    }

    if (-not $SkipFrontend) {
        Write-Host "[4/5] Frontend typecheck + static export..." -ForegroundColor Gray
        Push-Location $Frontend
        try {
            if (-not (Test-Path "node_modules")) {
                npm ci --no-fund --no-audit
            }
            npm run typecheck
            if ($LASTEXITCODE -ne 0) { throw "typecheck failed" }
            npm run build:personal
            if ($LASTEXITCODE -ne 0) { throw "build:personal failed" }
        } finally {
            Pop-Location
        }
    } else {
        Write-Host "[4/5] Frontend skipped" -ForegroundColor Yellow
    }

    if ($Desktop) {
        Write-Host "[5/5] Desktop bundle prep..." -ForegroundColor Gray
        Push-Location $Frontend
        try {
            npm run bundle:runtime
            if ($LASTEXITCODE -ne 0) { throw "bundle:runtime failed" }
        } finally {
            Pop-Location
        }
    } else {
        Write-Host "[5/5] Desktop bundle skipped (use -Desktop for tauri:build prep)" -ForegroundColor Gray
    }

    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host " prepare-build OK" -ForegroundColor Green
    Write-Host " Web:   python app_v2.py  -> http://127.0.0.1:7864" -ForegroundColor Green
    if ($Desktop) {
        Write-Host " Next: cd frontend && npm run tauri:build" -ForegroundColor Green
    } else {
        Write-Host " Next: cd frontend && npm run prebuild:release (desktop)" -ForegroundColor Green
    }
    Write-Host "========================================" -ForegroundColor Green
}
catch {
    Write-Host ""
    Write-Host "prepare-build FAILED: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
finally {
    Pop-Location
}
