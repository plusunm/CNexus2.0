# CNexus Personal Edition — release gate before production build
param(
    [switch]$Strict
)

$ErrorActionPreference = "Stop"
$ScriptDir = $PSScriptRoot
$Root = Split-Path -Parent $ScriptDir
$Frontend = Join-Path $Root "frontend"
$TauriDir = Join-Path $Frontend "src-tauri"
$ReportDir = Join-Path $Root "packaging\prebuild-rc"
$ReportPath = Join-Path $ReportDir "LATEST_GATE.txt"
$SmokePassPath = Join-Path $ReportDir "SMOKE_PASS.json"

$fail = 0
$warn = 0
$pass = 0
$lines = New-Object System.Collections.Generic.List[string]

function Add-Line($s) { $lines.Add($s) | Out-Null }
function Pass($msg) { $script:pass++; Add-Line "[PASS] $msg"; Write-Host "[PASS] $msg" -ForegroundColor Green }
function Warn($msg) { $script:warn++; Add-Line "[WARN] $msg"; Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Fail($msg) { $script:fail++; Add-Line "[FAIL] $msg"; Write-Host "[FAIL] $msg" -ForegroundColor Red }

function Test-SourceContains($path, $pattern, $label) {
    if (-not (Test-Path $path)) {
        Fail "$label — file missing: $path"
        return $false
    }
    $raw = Get-Content $path -Raw -Encoding UTF8
    if ($raw -match $pattern) {
        Pass $label
        return $true
    }
    Fail "$label — pattern not found in $(Split-Path $path -Leaf)"
    return $false
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Magenta
Write-Host " CNexus PERSONAL RELEASE GATE" -ForegroundColor Magenta
Write-Host "========================================" -ForegroundColor Magenta
Add-Line "CNexus PERSONAL RELEASE GATE"
Add-Line "Time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Add-Line "Strict: $Strict"
Add-Line ""

Add-Line "== GATE 0: Toolchain readiness =="
$toolchainScript = Join-Path $ScriptDir "prebuild-toolchain-check.ps1"
& powershell -NoProfile -ExecutionPolicy Bypass -File $toolchainScript -Quiet | Out-Host
if ($LASTEXITCODE -ne 0) {
    Fail "toolchain not ready — open VS x64 Native Tools"
} else {
    Pass "toolchain ready"
}

Add-Line ""
Add-Line "== GATE 1: Personal gateway layout =="
if (Test-Path (Join-Path $Root "app_v2.py")) { Pass "app_v2.py present" } else { Fail "app_v2.py missing" }
if (Test-Path (Join-Path $Root "src/gateway")) { Pass "src/gateway present" } else { Fail "src/gateway missing" }
if (Test-Path (Join-Path $Root "runtime/constitution")) { Pass "runtime/constitution present" } else { Fail "runtime/constitution missing" }
if (Test-Path (Join-Path $Root "ui/index.html")) { Pass "ui/ static export present" } else { Warn "ui/index.html missing — run npm run build:personal" }

Add-Line ""
Add-Line "== GATE 2: Desktop boot determinism =="
Test-SourceContains (Join-Path $TauriDir "src/boot_sequence.rs") "/v1/system/ready" "Rust polls /v1/system/ready"
Test-SourceContains (Join-Path $TauriDir "src/runtime_probe.rs") "7864" "runtime_probe uses :7864"
Test-SourceContains (Join-Path $TauriDir "cnexus-runtime-sidecar/src/main.rs") "Stdio::null" "sidecar stdout/stderr null"
Test-SourceContains (Join-Path $TauriDir "cnexus-runtime-sidecar/src/main.rs") "pythonw\.exe" "sidecar prefers pythonw.exe"

$conf = Get-Content (Join-Path $TauriDir "tauri.conf.json") -Raw | ConvertFrom-Json
$float = $conf.app.windows | Where-Object { $_.label -eq "float" } | Select-Object -First 1
if ($float.visible -eq $false) { Pass "float.visible=false" } else { Fail "float.visible must be false" }
if ($float.width -eq 360 -and $float.height -eq 228) { Pass "float 360x228" } else { Fail "float must be 360x228" }

$bootShell = Join-Path $Frontend "components/desktop/BootShellProtocolRoot.tsx"
$tauriTs = Join-Path $Frontend "lib/tauriDesktop.ts"
Test-SourceContains $tauriTs "listenRuntimeReady" "tauriDesktop listenRuntimeReady"
Test-SourceContains $bootShell "listenRuntimeReady" "BootShellProtocolRoot waits runtime-ready"
Test-SourceContains $bootShell "grantUiRender" "BootShellProtocolRoot grants UI render"

Add-Line ""
Add-Line "== GATE 3: Runtime bundle (if present) =="
$bundleMain = Join-Path $TauriDir "runtime-bundle/app/app_v2.py"
if (Test-Path $bundleMain) {
    Pass "runtime-bundle staged"
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $ScriptDir "verify-runtime-bundle.ps1") | Out-Host
    if ($LASTEXITCODE -ne 0) { Fail "verify-runtime-bundle failed" } else { Pass "verify-runtime-bundle" }
} else {
    Warn "runtime-bundle not staged yet — run npm run bundle:runtime before tauri:build"
}

Add-Line ""
Add-Line "== GATE 4: Smoke pass marker =="
if (Test-Path $SmokePassPath) {
    try {
        $smoke = Get-Content $SmokePassPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($smoke.passed -eq $true) {
            $at = [datetime]::Parse($smoke.at)
            $ageH = ((Get-Date) - $at).TotalHours
            Pass "SMOKE_PASS.json ready_ms=$($smoke.ready_ms) age=$([math]::Round($ageH,1))h"
            if ($Strict -and $ageH -gt 24) {
                Fail "SMOKE_PASS older than 24h — re-run npm run prebuild:smoke"
            }
        } elseif ($Strict) {
            Fail "SMOKE_PASS.json passed=false — run npm run prebuild:smoke"
        } else {
            Warn "SMOKE_PASS.json passed=false — run prebuild:smoke before build"
        }
    } catch {
        if ($Strict) { Fail "SMOKE_PASS.json invalid" } else { Warn "SMOKE_PASS.json unreadable" }
    }
} else {
    if ($Strict) {
        Fail "SMOKE_PASS.json missing — run npm run prebuild:smoke"
    } else {
        Warn "No SMOKE_PASS.json — run prebuild:smoke before tauri:build"
    }
}

Add-Line ""
Add-Line "========================================"
Add-Line "GATE SUMMARY: PASS=$pass WARN=$warn FAIL=$fail"
Add-Line "BUILD ALLOWED: $(if ($fail -eq 0) { 'YES (automated)' } else { 'NO' })"
Add-Line "========================================"

if (-not (Test-Path $ReportDir)) {
    New-Item -ItemType Directory -Force -Path $ReportDir | Out-Null
}
$lines | Set-Content -Path $ReportPath -Encoding UTF8
Write-Host ""
Write-Host "Report: $ReportPath" -ForegroundColor Cyan

if ($fail -gt 0) {
    Write-Host ""
    Write-Host "RELEASE GATE FAILED — do NOT run tauri:build" -ForegroundColor Red
    exit 1
}

Write-Host ""
if ($warn -gt 0) {
    Write-Host "RELEASE GATE PASSED (automated) with $warn warning(s)" -ForegroundColor Yellow
} else {
    Write-Host "RELEASE GATE PASSED (automated)" -ForegroundColor Green
}
Write-Host ""
Write-Host "Next: npm run prebuild:smoke -> npm run tauri:build" -ForegroundColor Cyan
exit 0
