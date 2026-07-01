# CNexus Personal Edition — bundle app_v2.py gateway for Tauri desktop installer
param(
    [switch]$SkipPythonDownload
)

$ErrorActionPreference = "Stop"
$ScriptDir = $PSScriptRoot
$RepoRoot = Resolve-Path (Join-Path $ScriptDir "..")
$BundleRoot = Join-Path $RepoRoot "frontend/src-tauri/runtime-bundle"
$AppRoot = Join-Path $BundleRoot "app"
$PythonRoot = Join-Path $BundleRoot "python"
$SitePackages = Join-Path $PythonRoot "Lib/site-packages"
$WheelDir = Join-Path $BundleRoot "wheels"

function Invoke-DirectWebRequest {
    param(
        [Parameter(Mandatory)][string]$Uri,
        [Parameter(Mandatory)][string]$OutFile
    )
    $prevProxy = [System.Net.WebRequest]::DefaultWebProxy
    try {
        [System.Net.WebRequest]::DefaultWebProxy = $null
        for ($i = 1; $i -le 3; $i++) {
            try {
                if (Get-Command curl.exe -ErrorAction SilentlyContinue) {
                    & curl.exe --noproxy "*" -L --connect-timeout 60 --max-time 600 -o $OutFile $Uri
                    if ($LASTEXITCODE -eq 0 -and (Test-Path $OutFile) -and ((Get-Item $OutFile).Length -gt 1MB)) {
                        return
                    }
                }
                Invoke-WebRequest -Uri $Uri -OutFile $OutFile -UseBasicParsing -TimeoutSec 600
                return
            } catch {
                Write-Warning "Download attempt $i of 3 failed: $($_.Exception.Message)"
                if ($i -lt 3) { Start-Sleep -Seconds 3 }
                else { throw }
            }
        }
    } finally {
        [System.Net.WebRequest]::DefaultWebProxy = $prevProxy
    }
}

function Invoke-PipDirect {
    param([Parameter(Mandatory)][string[]]$PipArgs)
    $saved = @{}
    foreach ($name in @('HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'http_proxy', 'https_proxy', 'PIP_PROXY')) {
        if (Test-Path "Env:$name") { $saved[$name] = (Get-Item "Env:$name").Value }
        Remove-Item "Env:$name" -ErrorAction SilentlyContinue
    }
    $savedNoProxy = $env:NO_PROXY
    $savedNoProxyLower = $env:no_proxy
    $env:NO_PROXY = '*'
    $env:no_proxy = '*'
    try {
        $prevEap = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        $pipOut = & pip @PipArgs 2>&1
        $ErrorActionPreference = $prevEap
        $pipOut | ForEach-Object { Write-Host $_ }
        if ($LASTEXITCODE -ne 0) {
            $text = ($pipOut | Out-String)
            if ($text -match 'Successfully installed') {
                Write-Warning "pip exit $LASTEXITCODE ignored (packages appear installed)"
            } else {
                exit $LASTEXITCODE
            }
        }
    } finally {
        foreach ($name in $saved.Keys) { Set-Item -Path "Env:$name" -Value $saved[$name] }
        if ($null -ne $savedNoProxy) { $env:NO_PROXY = $savedNoProxy } else { Remove-Item Env:NO_PROXY -ErrorAction SilentlyContinue }
        if ($null -ne $savedNoProxyLower) { $env:no_proxy = $savedNoProxyLower } else { Remove-Item Env:no_proxy -ErrorAction SilentlyContinue }
    }
}

function Stop-RuntimeBundleLockers {
    Write-Host "-> Stopping processes that may lock runtime-bundle..."
    & (Join-Path $ScriptDir "kill-cnexus-runtime.ps1") | Out-Host
    Start-Sleep -Seconds 2
}

function Write-PythonPth {
    param([Parameter(Mandatory)][string]$Dest)
    $siteEntry = "Lib\site-packages"
    @(
        "python311.zip"
        "."
        "..\app"
        $siteEntry
        "import site"
    ) | Set-Content (Join-Path $Dest "python311._pth") -Encoding ASCII
}

function Install-EmbeddedPythonFromZip {
    param(
        [Parameter(Mandatory)][string]$Dest,
        [Parameter(Mandatory)][string]$EmbedZip,
        [Parameter(Mandatory)][string[]]$EmbedUrls
    )
    $embedMinBytes = 10MB
    New-Item -ItemType Directory -Force -Path (Split-Path $EmbedZip -Parent) | Out-Null
    if (-not ((Test-Path $EmbedZip) -and ((Get-Item $EmbedZip).Length -ge $embedMinBytes))) {
        Write-Host "-> Downloading Python 3.11 embeddable..."
        $downloaded = $false
        foreach ($url in $EmbedUrls) {
            try {
                Write-Host "   try: $url"
                Invoke-DirectWebRequest -Uri $url -OutFile $EmbedZip
                if ((Test-Path $EmbedZip) -and (Get-Item $EmbedZip).Length -ge $embedMinBytes) {
                    $downloaded = $true
                    break
                }
            } catch {
                Write-Warning "Download failed: $($_.Exception.Message)"
            }
            Remove-Item $EmbedZip -Force -ErrorAction SilentlyContinue
        }
        if (-not $downloaded) { throw "Could not download Python embed zip." }
    } else {
        Write-Host "-> Using cached Python embed zip"
    }
    New-Item -ItemType Directory -Force -Path $Dest | Out-Null
    $expandZip = Join-Path $env:TEMP "cnexus-python-embed-expand-$(Get-Random).zip"
    Copy-Item -Force $EmbedZip $expandZip
    try {
        Expand-Archive -Path $expandZip -DestinationPath $Dest -Force
    } finally {
        Remove-Item $expandZip -Force -ErrorAction SilentlyContinue
    }
}

Write-Host "== CNexus Personal runtime bundle ==" -ForegroundColor Cyan
Write-Host "Repo:   $RepoRoot"
Write-Host "Bundle: $BundleRoot"

Stop-RuntimeBundleLockers

if (Test-Path $BundleRoot) {
    foreach ($child in @("wheels", "app")) {
        $target = Join-Path $BundleRoot $child
        if (Test-Path $target) { Remove-Item $target -Recurse -Force -ErrorAction SilentlyContinue }
    }
    if (Test-Path $SitePackages) {
        Remove-Item $SitePackages -Recurse -Force -ErrorAction SilentlyContinue
    }
} else {
    New-Item -ItemType Directory -Force -Path $BundleRoot | Out-Null
}

New-Item -ItemType Directory -Force -Path $AppRoot, $PythonRoot, $SitePackages, $WheelDir | Out-Null

if (-not $SkipPythonDownload) {
    $EmbedZip = Join-Path $RepoRoot "scripts/cache/python-3.11.9-embed-amd64.zip"
    $EmbedUrls = @(
        "https://registry.npmmirror.com/-/binary/python/3.11.9/python-3.11.9-embed-amd64.zip"
        "https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip"
    )
    if (-not (Test-Path (Join-Path $PythonRoot "python.exe"))) {
        Install-EmbeddedPythonFromZip -Dest $PythonRoot -EmbedZip $EmbedZip -EmbedUrls $EmbedUrls
    }
    Write-PythonPth -Dest $PythonRoot
} else {
    Write-Host "-> SkipPythonDownload: ensure python/ has embed layout"
}

if (-not (Test-Path (Join-Path $PythonRoot "pythonw.exe"))) {
    throw "pythonw.exe missing — re-run bundle without -SkipPythonDownload"
}

Write-Host "-> Copying Personal gateway (app_v2.py + src + runtime)..."
foreach ($item in @("app_v2.py", "src", "runtime")) {
    $src = Join-Path $RepoRoot $item
    if (-not (Test-Path $src)) { throw "Missing repo item: $item" }
    $dest = Join-Path $AppRoot $item
    if (Test-Path $dest) { Remove-Item $dest -Recurse -Force }
    Copy-Item -Recurse -Force $src $dest
}

$uiSrc = Join-Path $RepoRoot "ui"
if (Test-Path $uiSrc) {
    Copy-Item -Recurse -Force $uiSrc (Join-Path $AppRoot "ui")
    Write-Host "-> Copied ui/ static export"
} else {
    Write-Warning "ui/ missing — run npm run build:personal first for bundled static UI"
}

$templates = Join-Path $AppRoot "data-templates"
New-Item -ItemType Directory -Force -Path $templates | Out-Null
$logTemplate = '{"event":"BUNDLE_TEMPLATE","level":"info","source":"bundle","message":"Runtime conflict monitor log"}'
Set-Content -Path (Join-Path $templates "runtime-conflict-monitor.log") -Value $logTemplate -Encoding UTF8

$cfgSrc = Join-Path $RepoRoot "frontend/public/cnexus-config.json"
$cfgDest = Join-Path $AppRoot "cnexus-config.json"
if (Test-Path $cfgSrc) {
    Copy-Item -Force $cfgSrc $cfgDest
    Write-Host "-> Copied frontend/public/cnexus-config.json (bootstrap peers)"
} else {
    Write-Warning "frontend/public/cnexus-config.json missing — run write-cnexus-config.mjs first"
    @{
        edition = "personal"
        apiBase = "http://127.0.0.1:7864"
        wsBase = ""
    } | ConvertTo-Json -Compress | Set-Content -Path $cfgDest -Encoding UTF8
}

Write-Host "-> Installing Python deps (pynacl) to site-packages..."
$req = Join-Path $RepoRoot "requirements.txt"
Invoke-PipDirect -PipArgs @(
    'install', '--upgrade', '--no-cache-dir',
    '-r', $req,
    '--target', $SitePackages
)

& (Join-Path $ScriptDir "verify-runtime-bundle.ps1")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "== Done. runtime-bundle ready for tauri build ==" -ForegroundColor Green
