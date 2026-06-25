# CNexus 2.0 desktop dev — float window (Tauri) + app_v2.py gateway on :7864
# Usage:
#   dev-desktop.ps1 browser   # browser http://localhost:3000/desktop
#   dev-desktop.ps1 tauri     # Tauri float window + hot reload (default)
param(
    [ValidateSet("browser", "tauri")]
    [string]$Mode = "tauri"
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Frontend = Join-Path $RepoRoot "frontend"
$GatewayPort = 7864

function Test-CnexusGatewayHealthy {
    foreach ($path in @("/health", "/v1/health", "/api/status")) {
        try {
            $r = Invoke-WebRequest -Uri "http://127.0.0.1:${GatewayPort}$path" -TimeoutSec 2 -UseBasicParsing
            if ($r.StatusCode -ne 200) { continue }
            $body = $r.Content.ToLowerInvariant()
            if ($body -match "cnexus" -or $body -match '"status"\s*:\s*"(ok|ready|warming)"') {
                return $true
            }
        } catch { }
    }
    return $false
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  CNexus 2.0 Desktop DEV" -ForegroundColor Cyan
Write-Host "  Mode: $Mode" -ForegroundColor Gray
Write-Host "  Gateway: http://127.0.0.1:$GatewayPort" -ForegroundColor Gray
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if (Test-CnexusGatewayHealthy) {
    Write-Host "[OK] Reusing gateway on :$GatewayPort" -ForegroundColor Green
} else {
    Write-Host "Starting hidden gateway..." -ForegroundColor Gray
    $vbs = Join-Path $RepoRoot "run_gateway_hidden.vbs"
    if (-not (Test-Path $vbs)) {
        Write-Host "FAIL: missing $vbs" -ForegroundColor Red
        exit 1
    }
    wscript.exe //nologo $vbs
    $ready = $false
    for ($i = 0; $i -lt 40; $i++) {
        if (Test-CnexusGatewayHealthy) { $ready = $true; break }
        Start-Sleep -Milliseconds 500
    }
    if ($ready) {
        Write-Host "[OK] Gateway ready http://127.0.0.1:$GatewayPort" -ForegroundColor Green
    } else {
        Write-Host "[WARN] Gateway not healthy yet; float UI may retry." -ForegroundColor Yellow
        $log = Join-Path $RepoRoot "gateway.log"
        if (Test-Path $log) {
            Write-Host "--- gateway.log tail ---" -ForegroundColor DarkGray
            Get-Content -LiteralPath $log -Tail 15 -ErrorAction SilentlyContinue
        }
    }
}

Set-Location $Frontend
if (-not (Test-Path "node_modules")) {
    Write-Host "First run: npm install..." -ForegroundColor Gray
    npm install --no-fund --no-audit
}

$env:CNEXUS_API_BASE = "http://127.0.0.1:$GatewayPort"
$env:CNEXUS_GATEWAY_PORT = "$GatewayPort"
$env:CNEXUS_DEV_REPO = $RepoRoot
$env:CNEXUS_TAURI = "1"
node scripts/write-cnexus-config.mjs personal | Out-Host

if ($Mode -eq "browser") {
    Write-Host ""
    Write-Host "Browser dev: http://localhost:3000/desktop" -ForegroundColor Green
    Write-Host "API: http://127.0.0.1:$GatewayPort" -ForegroundColor Green
    Start-Process "http://localhost:3000/desktop"
    npm run dev
    exit 0
}

$iconIco = Join-Path $Frontend "src-tauri\icons\icon.ico"
if (-not (Test-Path $iconIco)) {
    Write-Host "First run: generating Tauri icons..." -ForegroundColor Gray
    npm run tauri:icons
}

Write-Host ""
Write-Host "Tauri dev: float window + hot reload" -ForegroundColor Green
Write-Host "Stop with Ctrl+C (gateway keeps running — use stop_cnexus.bat)" -ForegroundColor Gray
npx tauri dev
