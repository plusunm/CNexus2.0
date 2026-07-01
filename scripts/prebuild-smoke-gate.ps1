# CNexus Personal Edition — live runtime smoke gate (app_v2 on :7864)
param(
    [int]$ReadyTimeoutSec = 45
)

$ErrorActionPreference = "Stop"
$ScriptDir = $PSScriptRoot
$Root = Split-Path -Parent $ScriptDir
$TauriDir = Join-Path $Root "frontend/src-tauri"
$ReportDir = Join-Path $Root "packaging\prebuild-rc"
$ReportPath = Join-Path $ReportDir "LATEST_SMOKE.txt"
$PassMarker = Join-Path $ReportDir "SMOKE_PASS.json"

$fail = 0
$pass = 0
$warn = 0
$lines = New-Object System.Collections.Generic.List[string]
$metrics = @{}

function Add-Line($s) { $lines.Add($s) | Out-Null }
function Pass($msg) { $script:pass++; Add-Line "[PASS] $msg"; Write-Host "[PASS] $msg" -ForegroundColor Green }
function Warn($msg) { $script:warn++; Add-Line "[WARN] $msg"; Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Fail($msg) { $script:fail++; Add-Line "[FAIL] $msg"; Write-Host "[FAIL] $msg" -ForegroundColor Red }

function Stop-SmokeRuntime {
    & (Join-Path $ScriptDir "kill-cnexus-runtime.ps1") | Out-Null
}

function Test-PortListening($port) {
    return [bool](Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " CNexus PERSONAL RUNTIME SMOKE GATE" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Add-Line "CNexus PERSONAL RUNTIME SMOKE GATE"
Add-Line "Time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Add-Line ""

Add-Line "== Preflight =="
$sidecar = Join-Path $TauriDir "cnexus-runtime-x86_64-pc-windows-msvc.exe"
$bundleMain = Join-Path $TauriDir "runtime-bundle/app/app_v2.py"
$devGateway = Join-Path $Root "app_v2.py"

if (Test-Path $sidecar) { Pass "sidecar exe present" } else { Warn "sidecar missing — will smoke-test dev gateway only" }
if (Test-Path $bundleMain) { Pass "runtime-bundle present" } elseif (Test-Path $devGateway) { Pass "dev app_v2.py present (bundle optional for web build)" } else { Fail "no gateway to smoke-test" }

$useSidecar = (Test-Path $sidecar) -and (Test-Path $bundleMain)
if (-not $useSidecar -and (Test-Path $sidecar)) {
    Warn "sidecar present but runtime-bundle missing — using dev app_v2.py for smoke"
}

Stop-SmokeRuntime
Pass "port 7864 cleared before smoke"

$dataRoot = Join-Path $env:LOCALAPPDATA "CNexus\data"
New-Item -ItemType Directory -Force -Path (Join-Path $dataRoot "blocks") | Out-Null
Pass "memory data dirs ensured"

Add-Line ""
Add-Line "== Live runtime boot =="
$runtimeProc = $null
$swTotal = [System.Diagnostics.Stopwatch]::StartNew()
$lastReadyErr = $null

try {
    if ($useSidecar) {
        $runtimeProc = Start-Process -FilePath $sidecar -PassThru -WindowStyle Hidden
        Pass "spawned cnexus-runtime pid=$($runtimeProc.Id)"
    } else {
        $python = Get-Command python -ErrorAction SilentlyContinue
        if (-not $python) { throw "python not found for dev smoke" }
        $runtimeProc = Start-Process -FilePath $python.Source -ArgumentList @("-B", "-u", "app_v2.py") -WorkingDirectory $Root -PassThru -WindowStyle Hidden
        Pass "spawned dev app_v2.py pid=$($runtimeProc.Id)"
    }

    $deadline = (Get-Date).AddSeconds($ReadyTimeoutSec)
    $readyPayload = $null
    $swReady = [System.Diagnostics.Stopwatch]::StartNew()
    while ((Get-Date) -lt $deadline) {
        if ($runtimeProc.HasExited) {
            Fail "runtime exited early code=$($runtimeProc.ExitCode)"
            break
        }
        try {
            $resp = Invoke-RestMethod -Uri "http://127.0.0.1:7864/v1/system/ready" -TimeoutSec 3 -Method Get
            if ($resp.status -eq "ready") {
                $readyPayload = $resp
                break
            }
            $lastReadyErr = "status=$($resp.status)"
        } catch {
            $lastReadyErr = $_.Exception.Message
        }
        Start-Sleep -Milliseconds 250
    }
    $swReady.Stop()
    $metrics.ready_ms = [int]$swReady.ElapsedMilliseconds

    if (-not $readyPayload) {
        if ($lastReadyErr) { Add-Line "last /v1/system/ready error: $lastReadyErr" }
        Fail "/v1/system/ready not ready within ${ReadyTimeoutSec}s"
    } else {
        Pass "/v1/system/ready in $($metrics.ready_ms)ms"
    }

    try {
        $status = Invoke-RestMethod -Uri "http://127.0.0.1:7864/api/status" -TimeoutSec 3
        if ($status.status -match "ok|ready|warming|online") { Pass "/api/status ok" } else { Fail "/api/status unexpected ($($status.status))" }
    } catch {
        Fail "/api/status failed after ready"
    }

    try {
        $analyzeBody = @{
            text = "他最近不理我"
            fast = $true
            use_llm = $false
            save_card = $false
        } | ConvertTo-Json -Compress
        $analyze = Invoke-RestMethod -Uri "http://127.0.0.1:7864/api/analyze" -Method Post `
            -ContentType "application/json; charset=utf-8" -Body $analyzeBody -TimeoutSec 15
        if ($analyze.ok -ne $true -or -not $analyze.analysis) {
            Fail "/api/analyze missing ok/analysis"
        } elseif (-not $analyze.analysis.state) {
            Fail "/api/analyze analysis missing state"
        } else {
            Pass "/api/analyze fast ok"
        }
    } catch {
        Fail "/api/analyze failed: $($_.Exception.Message)"
    }

    try {
        $boot = Invoke-RestMethod -Uri "http://127.0.0.1:7864/v1/runtime/boot" -TimeoutSec 3
        if ($boot.boot_id) { Pass "/v1/runtime/boot boot_id=$($boot.boot_id)" } else { Warn "/v1/runtime/boot missing boot_id" }
    } catch {
        Warn "/v1/runtime/boot probe failed (non-fatal for web build)"
    }

    Add-Line ""
    Add-Line "== Shutdown probe =="
    if ($runtimeProc -and -not $runtimeProc.HasExited) {
        $null = Start-Process -FilePath "taskkill" -ArgumentList @("/F", "/T", "/PID", "$($runtimeProc.Id)") -WindowStyle Hidden -Wait
        Pass "sent taskkill to pid=$($runtimeProc.Id)"
        $swShutdown = [System.Diagnostics.Stopwatch]::StartNew()
        while ($swShutdown.ElapsedMilliseconds -lt 5000) {
            if (-not (Test-PortListening 7864)) { break }
            Start-Sleep -Milliseconds 200
        }
        $metrics.shutdown_ms = [int]$swShutdown.ElapsedMilliseconds
        if (Test-PortListening 7864) {
            Fail "port 7864 still listening after shutdown"
            Stop-SmokeRuntime
        } else {
            Pass "port 7864 released in $($metrics.shutdown_ms)ms"
        }
        $runtimeProc = $null
    }
}
finally {
    if ($runtimeProc -and -not $runtimeProc.HasExited) {
        Stop-Process -Id $runtimeProc.Id -Force -ErrorAction SilentlyContinue
    }
    Stop-SmokeRuntime
    $swTotal.Stop()
    $metrics.total_ms = [int]$swTotal.ElapsedMilliseconds
    Pass "cleanup complete (total $($metrics.total_ms)ms)"
}

Add-Line ""
Add-Line "metrics: ready_ms=$($metrics.ready_ms) shutdown_ms=$($metrics.shutdown_ms) total_ms=$($metrics.total_ms)"
Add-Line "SMOKE SUMMARY: PASS=$pass WARN=$warn FAIL=$fail"

if (-not (Test-Path $ReportDir)) {
    New-Item -ItemType Directory -Force -Path $ReportDir | Out-Null
}
$lines | Set-Content -Path $ReportPath -Encoding UTF8

if ($fail -eq 0) {
    @{
        passed = $true
        at = (Get-Date).ToString("o")
        ready_ms = $metrics.ready_ms
        shutdown_ms = $metrics.shutdown_ms
        total_ms = $metrics.total_ms
        edition = "personal"
        port = 7864
    } | ConvertTo-Json | Set-Content -Path $PassMarker -Encoding UTF8
    Write-Host ""
    Write-Host "SMOKE GATE PASSED" -ForegroundColor Green
    Write-Host "Report: $ReportPath" -ForegroundColor Cyan
    exit 0
}

@{
    passed = $false
    at = (Get-Date).ToString("o")
    ready_ms = $metrics.ready_ms
    total_ms = $metrics.total_ms
} | ConvertTo-Json | Set-Content -Path $PassMarker -Encoding UTF8

Write-Host ""
Write-Host "SMOKE GATE FAILED" -ForegroundColor Red
Write-Host "Report: $ReportPath" -ForegroundColor Cyan
exit 1
