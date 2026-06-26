# Force-stop CNexus UI + Runtime sidecar + app_v2 gateway (orphan cleanup)
$ErrorActionPreference = "SilentlyContinue"

Write-Host "Stopping CNexus processes..." -ForegroundColor Cyan

foreach ($exe in @("CNexus.exe", "cnexus-product.exe", "cnexus-runtime.exe")) {
    taskkill /F /T /IM $exe 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) { Write-Host "  killed $exe" }
}

$pyNames = @("python.exe", "pythonw.exe")
Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
    ($pyNames -contains $_.Name) -and $_.CommandLine -and (
        $_.CommandLine -match "app_v2\.py" -or
        $_.CommandLine -match "runtime-bundle" -or
        $_.CommandLine -match "CNexus2\.0"
    )
} | ForEach-Object {
    Write-Host "  kill $($_.Name) pid $($_.ProcessId)"
    Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
}

Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
    ($_.Name -eq "node.exe") -and $_.CommandLine -and (
        $_.CommandLine -match "CNexus2\.0\\frontend" -or
        $_.CommandLine -match "next dev" -or
        $_.CommandLine -match "tauri dev"
    )
} | ForEach-Object {
    Write-Host "  kill $($_.Name) pid $($_.ProcessId)"
    taskkill /F /T /PID $_.ProcessId 2>$null | Out-Null
}

foreach ($port in @(7864, 3000)) {
    Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
        ForEach-Object {
            Write-Host "  kill port $port pid $($_.OwningProcess)"
            taskkill /F /T /PID $_.OwningProcess 2>$null | Out-Null
        }
}

$portsDown = @()
foreach ($port in @(7864, 3000)) {
    $listening = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if ($listening) {
        Write-Host "WARN: :$port still listening — run as Admin or reboot" -ForegroundColor Yellow
    } else {
        $portsDown += ":$port"
    }
}

$healthOk = $false
try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:7864/api/status" -TimeoutSec 2 -UseBasicParsing
    $healthOk = $r.StatusCode -eq 200
} catch {
    $healthOk = $false
}

if ($healthOk) {
    Write-Host "WARN: :7864 still responds — run as Admin or reboot" -ForegroundColor Yellow
} elseif ($portsDown.Count -gt 0) {
    Write-Host ("Done. {0} released." -f ($portsDown -join ", ")) -ForegroundColor Green
} else {
    Write-Host "Done." -ForegroundColor Green
}
