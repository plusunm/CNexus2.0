# Verify Personal Edition runtime-bundle before tauri build
$ErrorActionPreference = "Stop"
$ScriptDir = $PSScriptRoot
$Root = Resolve-Path (Join-Path $ScriptDir "..")
$Bundle = Join-Path $Root "frontend/src-tauri/runtime-bundle"

$required = @(
    "app/app_v2.py"
    "app/src/gateway/__init__.py"
    "app/runtime/constitution/cognitive_constitution.md"
    "app/runtime/policy/reasoning_policy.md"
    "app/cnexus-config.json"
    "app/data-templates/runtime-conflict-monitor.log"
    "python/python.exe"
    "python/pythonw.exe"
    "python/python311.zip"
)

Write-Host ""
Write-Host "=== CNexus runtime-bundle verify (Personal Edition) ===" -ForegroundColor Cyan

if (-not (Test-Path $Bundle)) {
    Write-Host "[FAIL] runtime-bundle missing: $Bundle" -ForegroundColor Red
    Write-Host "       Run: npm run bundle:runtime" -ForegroundColor Yellow
    exit 1
}

$missing = @()
foreach ($rel in $required) {
    $path = Join-Path $Bundle $rel
    if (Test-Path $path) {
        Write-Host "[OK] $rel" -ForegroundColor Green
    } else {
        Write-Host "[FAIL] $rel" -ForegroundColor Red
        $missing += $rel
    }
}

$foundationDir = Join-Path $Bundle "app/runtime/foundation"
$foundationDocs = @(Get-ChildItem -Path $foundationDir -Filter "*.md" -ErrorAction SilentlyContinue)
if ($foundationDocs.Count -gt 0) {
    Write-Host "[OK] app/runtime/foundation ($($foundationDocs.Count) manual doc(s))" -ForegroundColor Green
} else {
    Write-Host "[FAIL] app/runtime/foundation — no user manual .md" -ForegroundColor Red
    $missing += "app/runtime/foundation/*.md"
}

$sitePackages = Join-Path $Bundle "python/Lib/site-packages"
$nacl = Join-Path $sitePackages "nacl"
if (Test-Path $nacl) {
    Write-Host "[OK] python/Lib/site-packages/nacl" -ForegroundColor Green
} else {
    Write-Host "[FAIL] python/Lib/site-packages/nacl (pynacl)" -ForegroundColor Red
    $missing += "python/Lib/site-packages/nacl"
}

$uiIndex = Join-Path $Bundle "app/ui/index.html"
if (Test-Path $uiIndex) {
    Write-Host "[OK] app/ui/index.html" -ForegroundColor Green
} else {
    Write-Host "[WARN] app/ui/index.html missing — run npm run build:personal before bundle:runtime" -ForegroundColor Yellow
}

Write-Host ""
if ($missing.Count -gt 0) {
    Write-Host "runtime-bundle INCOMPLETE. Missing:" -ForegroundColor Red
    $missing | ForEach-Object { Write-Host "  - $_" -ForegroundColor Red }
    Write-Host "Run: npm run build:personal && npm run bundle:runtime" -ForegroundColor Yellow
    exit 1
}

$pyExe = Join-Path $Bundle "python/python.exe"
$site = $sitePackages
$appRoot = Join-Path $Bundle "app"
Write-Host "-> Smoke test bundled python + pynacl..." -ForegroundColor Cyan
$prevHome = $env:PYTHONHOME
$prevPath = $env:PYTHONPATH
$env:PYTHONHOME = $null
$env:PYTHONPATH = "$appRoot;$site"
$pyOut = & $pyExe -c "import encodings; import nacl.signing; print('python runtime OK')" 2>&1
$env:PYTHONHOME = $prevHome
$env:PYTHONPATH = $prevPath
$pyOut | ForEach-Object { Write-Host $_ }
if ($LASTEXITCODE -ne 0) {
    Write-Host "[FAIL] bundled python cannot import pynacl" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] python smoke test" -ForegroundColor Green

Write-Host "runtime-bundle OK for tauri build" -ForegroundColor Green
Write-Host ""
exit 0
