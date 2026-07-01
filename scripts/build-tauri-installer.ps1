param(
    [switch]$TauriOnly,
    [switch]$SkipGate
)

# CNexus Personal Edition — build NSIS installer (*.exe setup)
$ErrorActionPreference = "Stop"
$ScriptDir = $PSScriptRoot
$Root = Split-Path -Parent $ScriptDir
$Frontend = Join-Path $Root "frontend"
$TauriDir = Join-Path $Frontend "src-tauri"

function Import-VcVars64 {
    param([string]$VcvarsBat)
    $lines = cmd /c "`"$VcvarsBat`" >nul 2>&1 && set"
    foreach ($line in $lines) {
        if ($line -notmatch "=") { continue }
        $idx = $line.IndexOf("=")
        $name = $line.Substring(0, $idx)
        $value = $line.Substring($idx + 1)
        Set-Item -Path "Env:$name" -Value $value
    }
}

$vcvars = Get-ChildItem (Join-Path ${env:ProgramFiles(x86)} "Microsoft Visual Studio") -Recurse -Filter "vcvars64.bat" -ErrorAction SilentlyContinue |
    Select-Object -First 1 -ExpandProperty FullName
if (-not $vcvars) {
    throw "vcvars64.bat not found — install Visual Studio Build Tools (Desktop C++)"
}

Write-Host "Using MSVC env: $vcvars" -ForegroundColor Cyan
& (Join-Path $ScriptDir "kill-cnexus-runtime.ps1") | Out-Null

Import-VcVars64 $vcvars
$env:CARGO_TARGET_DIR = Join-Path $TauriDir "target"

Push-Location $Frontend
try {
    if (-not $SkipGate) {
        Write-Host "Running prebuild:release gate..." -ForegroundColor Cyan
        npm run prebuild:release
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
    Write-Host "Starting $(if ($TauriOnly) { 'npx tauri build' } else { 'npm run tauri:build' })..." -ForegroundColor Cyan
    if ($TauriOnly) {
        npx tauri build
    } else {
        npm run tauri:build
    }
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} finally {
    Pop-Location
}

$bundleDir = Join-Path $TauriDir "target\release\bundle\nsis"
if (Test-Path $bundleDir) {
    Write-Host ""
    Write-Host "Installer output:" -ForegroundColor Green
    Get-ChildItem $bundleDir -Filter "*.exe" | ForEach-Object { Write-Host "  $($_.FullName)" -ForegroundColor Green }
}
