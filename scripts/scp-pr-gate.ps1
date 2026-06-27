# CNexus SCP PR Gate — SBSL 100-turn creep + invariant tests (spec §11)
param(
    [switch]$Quiet
)

$ErrorActionPreference = "Stop"
$ScriptDir = $PSScriptRoot
$Root = Split-Path -Parent $ScriptDir
$ReportDir = Join-Path $Root "packaging\prebuild-rc"
$ReportPath = Join-Path $ReportDir "LATEST_SCP_GATE.txt"
$PassMarker = Join-Path $ReportDir "SCP_PASS.json"

$fail = 0
$pass = 0
$lines = New-Object System.Collections.Generic.List[string]

function Add-Line($s) { $lines.Add($s) | Out-Null }
function Pass($msg) { $script:pass++; Add-Line "[PASS] $msg"; if (-not $Quiet) { Write-Host "[PASS] $msg" -ForegroundColor Green } }
function Fail($msg) { $script:fail++; Add-Line "[FAIL] $msg"; if (-not $Quiet) { Write-Host "[FAIL] $msg" -ForegroundColor Red } }

if (-not $Quiet) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host " CNexus SCP PR GATE (P0-P4)" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
}
Add-Line "CNexus SCP PR GATE"
Add-Line "Time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Add-Line ""

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Fail "python not found"
    exit 1
}
Pass "python $($python.Source)"

Push-Location $Root
try {
    $testFiles = @(
        "tests/test_scp_pass_through.py",
        "tests/test_scp_sbsl_drift.py",
        "tests/test_scp_p1.py",
        "tests/test_scp_p2.py",
        "tests/test_scp_p3.py",
        "tests/test_scp_p4.py"
    )
    $args = @("-m", "pytest") + $testFiles + @("-q", "--tb=short")
    $output = & python @args 2>&1
    $exitCode = $LASTEXITCODE
    $output | ForEach-Object { Add-Line $_ }
    if ($exitCode -ne 0) {
        Fail "pytest SCP suite failed (exit $exitCode)"
    } else {
        Pass "pytest SCP suite ($($testFiles.Count) files)"
    }
}
finally {
    Pop-Location
}

Add-Line ""
Add-Line "SCP GATE SUMMARY: PASS=$pass FAIL=$fail"

if (-not (Test-Path $ReportDir)) {
    New-Item -ItemType Directory -Force -Path $ReportDir | Out-Null
}
$lines | Set-Content -Path $ReportPath -Encoding UTF8

if ($fail -eq 0) {
    @{
        passed = $true
        at = (Get-Date).ToString("o")
        gate = "scp-p0-p4"
        spec = "11_semantic_control_plane.md"
    } | ConvertTo-Json | Set-Content -Path $PassMarker -Encoding UTF8
    if (-not $Quiet) {
        Write-Host ""
        Write-Host "SCP PR GATE PASSED" -ForegroundColor Green
        Write-Host "Report: $ReportPath" -ForegroundColor Cyan
    }
    exit 0
}

@{
    passed = $false
    at = (Get-Date).ToString("o")
    gate = "scp-p0-p4"
} | ConvertTo-Json | Set-Content -Path $PassMarker -Encoding UTF8

if (-not $Quiet) {
    Write-Host ""
    Write-Host "SCP PR GATE FAILED" -ForegroundColor Red
    Write-Host "Report: $ReportPath" -ForegroundColor Cyan
}
exit 1
