# CNexus desktop — kill stale Runtime, check Ollama, launch UI, wait for API liveness.
# Use as PRE-START launcher (desktop shortcut), not inside Tauri setup().
param(
    [string]$ExePath = "",
    [switch]$SkipKill,
    [switch]$SkipOllama,
    [switch]$TryStartOllama,
    [switch]$NoLaunch,
    [int]$ApiWaitSec = 90,
    [int]$OllamaWaitSec = 20
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

function Write-Step {
    param([string]$Message, [string]$Color = "Cyan")
    Write-Host ""
    Write-Host "== $Message" -ForegroundColor $Color
}

function Resolve-RepoRoot {
    param([string]$ScriptRoot)
    $dir = $ScriptRoot
    for ($i = 0; $i -lt 6; $i++) {
        if (Test-Path (Join-Path $dir "brain-memory-ui\frontend\src-tauri\tauri.conf.json")) {
            return (Resolve-Path $dir).Path
        }
        $parent = Split-Path $dir -Parent
        if (-not $parent -or $parent -eq $dir) { break }
        $dir = $parent
    }
    return $null
}

function Resolve-CNexusProductExe {
    param([string]$Explicit, [string]$ScriptRoot)
    if ($Explicit) {
        $p = $Explicit.Trim('"')
        if (Test-Path $p) { return (Resolve-Path $p).Path }
        throw "CNexus exe not found: $p"
    }

    $repo = Resolve-RepoRoot -ScriptRoot $ScriptRoot
    $candidates = @(
        (Join-Path $ScriptRoot "cnexus-product.exe")
        (Join-Path $ScriptRoot "..\cnexus-product.exe")
        (Join-Path $ScriptRoot "..\..\cnexus-product.exe")
        (Join-Path $env:LOCALAPPDATA "Programs\CNexus\cnexus-product.exe")
        (Join-Path ${env:ProgramFiles} "CNexus\cnexus-product.exe")
        (Join-Path ${env:ProgramFiles(x86)} "CNexus\cnexus-product.exe")
    )
    if ($repo) {
        $candidates += (Join-Path $repo "brain-memory-ui\frontend\src-tauri\target\release\cnexus-product.exe")
    }

    foreach ($c in $candidates) {
        try {
            if ($c -and (Test-Path $c)) {
                return (Resolve-Path $c).Path
            }
        } catch { }
    }
    throw @"
找不到 cnexus-product.exe。
请指定: -ExePath 'C:\path\to\cnexus-product.exe'
或先执行 npm run tauri:build 生成 Release 包。
"@
}

function Test-OllamaReachable {
    param([int]$TimeoutSec = 3)
    $hosts = @("http://127.0.0.1:11434", "http://localhost:11434")
    if ($env:OLLAMA_HOST) {
        $hosts = @($env:OLLAMA_HOST.TrimEnd('/')) + $hosts | Select-Object -Unique
    }
    foreach ($host in $hosts) {
        try {
            $uri = "$host/api/tags"
            $r = Invoke-WebRequest -Uri $uri -TimeoutSec $TimeoutSec -UseBasicParsing
            if ($r.StatusCode -eq 200) {
                return @{ ok = $true; host = $host; detail = "HTTP 200" }
            }
        } catch {
            continue
        }
    }
    return @{ ok = $false; host = $null; detail = "connection refused or timeout" }
}

function Start-OllamaIfPossible {
    $cmd = Get-Command ollama -ErrorAction SilentlyContinue
    if ($cmd) {
        Write-Host "-> Starting: ollama serve (background)" -ForegroundColor Gray
        Start-Process -FilePath $cmd.Source -ArgumentList "serve" -WindowStyle Hidden -ErrorAction SilentlyContinue | Out-Null
        return $true
    }
    $appPaths = @(
        (Join-Path $env:LOCALAPPDATA "Programs\Ollama\Ollama.exe")
        (Join-Path ${env:ProgramFiles} "Ollama\Ollama.exe")
    )
    foreach ($app in $appPaths) {
        if (Test-Path $app) {
            Write-Host "-> Starting Ollama app: $app" -ForegroundColor Gray
            Start-Process -FilePath $app -WindowStyle Hidden -ErrorAction SilentlyContinue | Out-Null
            return $true
        }
    }
    return $false
}

function Wait-ApiHealth {
    param([int]$MaxSec = 90)
    $urls = @(
        "http://127.0.0.1:7864/v1/health"
        "http://127.0.0.1:7864/health"
    )
    $deadline = (Get-Date).AddSeconds($MaxSec)
    $i = 0
    while ((Get-Date) -lt $deadline) {
        $i++
        foreach ($url in $urls) {
            try {
                $r = Invoke-WebRequest -Uri $url -TimeoutSec 4 -UseBasicParsing
                if ($r.StatusCode -eq 200) {
                    return @{ ok = $true; url = $url; attempts = $i }
                }
            } catch { }
        }
        Write-Host "   waiting API ($i)..." -ForegroundColor DarkGray
        Start-Sleep -Seconds 2
    }
    return @{ ok = $false; url = $null; attempts = $i }
}

$ScriptDir = $PSScriptRoot
$KillScript = Join-Path $ScriptDir "kill-cnexus-runtime.ps1"

Write-Host ""
Write-Host "CNexus desktop restart launcher" -ForegroundColor White
Write-Host "  (pre-start: kill -> Ollama check -> launch -> API probe)" -ForegroundColor DarkGray

if (-not $SkipKill) {
    Write-Step "1/4 Stop stale CNexus / Runtime"
    if (Test-Path $KillScript) {
        & $KillScript
    } else {
        Write-Host "WARN: kill-cnexus-runtime.ps1 missing — skipping" -ForegroundColor Yellow
    }
    Start-Sleep -Seconds 2
} else {
    Write-Step "1/4 Skip kill (-SkipKill)" "Yellow"
}

if (-not $SkipOllama) {
    Write-Step "2/4 Check Ollama (127.0.0.1:11434)"
    $ollama = Test-OllamaReachable
    if ($ollama.ok) {
        Write-Host "[OK] Ollama reachable at $($ollama.host)" -ForegroundColor Green
    } else {
        Write-Host "[WARN] Ollama not reachable — embedding/chat may stay in warming" -ForegroundColor Yellow
        Write-Host "       Install: https://ollama.com  then run: ollama pull nomic-embed-text" -ForegroundColor DarkGray
        if ($TryStartOllama) {
            if (Start-OllamaIfPossible) {
                $deadline = (Get-Date).AddSeconds($OllamaWaitSec)
                while ((Get-Date) -lt $deadline) {
                    Start-Sleep -Seconds 2
                    $ollama = Test-OllamaReachable
                    if ($ollama.ok) {
                        Write-Host "[OK] Ollama came up at $($ollama.host)" -ForegroundColor Green
                        break
                    }
                }
                if (-not $ollama.ok) {
                    Write-Host "[WARN] Ollama still down after ${OllamaWaitSec}s — continuing anyway" -ForegroundColor Yellow
                }
            } else {
                Write-Host "       (ollama CLI/app not found; use -TryStartOllama only when installed)" -ForegroundColor DarkGray
            }
        }
    }
} else {
    Write-Step "2/4 Skip Ollama check (-SkipOllama)" "Yellow"
}

$productExe = Resolve-CNexusProductExe -Explicit $ExePath -ScriptRoot $ScriptDir
Write-Step "3/4 Launch CNexus"
Write-Host "-> $productExe" -ForegroundColor Gray

if ($NoLaunch) {
    Write-Host "NoLaunch set — done." -ForegroundColor Green
    exit 0
}

Start-Process -FilePath $productExe -WorkingDirectory (Split-Path $productExe -Parent) | Out-Null

Write-Step "4/4 Wait for gateway API (:7864)"
$api = Wait-ApiHealth -MaxSec $ApiWaitSec
if ($api.ok) {
    Write-Host "[OK] API responded: $($api.url)" -ForegroundColor Green
    Write-Host ""
    Write-Host "CNexus started. Float window should connect within ~30s." -ForegroundColor Green
    exit 0
}

Write-Host "[WARN] API did not respond within ${ApiWaitSec}s" -ForegroundColor Yellow
Write-Host "       Check: %LOCALAPPDATA%\CNexus\data\runtime-api.stderr.log" -ForegroundColor DarkGray
Write-Host "       UI may show Demo/Fallback — start Ollama and use this script again." -ForegroundColor DarkGray
exit 2
