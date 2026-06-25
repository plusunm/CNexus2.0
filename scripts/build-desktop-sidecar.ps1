# Build cnexus-runtime sidecar (spawns app_v2.py gateway)
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$SidecarManifest = Join-Path $RepoRoot "frontend/src-tauri/cnexus-runtime-sidecar/Cargo.toml"
$OutExe = Join-Path $RepoRoot "frontend/src-tauri/cnexus-runtime-sidecar/target/release/cnexus-runtime.exe"
$Dest = Join-Path $RepoRoot "frontend/src-tauri/cnexus-runtime-x86_64-pc-windows-msvc.exe"

Write-Host "== Build cnexus-runtime sidecar ==" -ForegroundColor Cyan
$cargoBin = Join-Path $env:USERPROFILE ".cargo\bin"
if (Test-Path $cargoBin) {
    $env:Path = "$cargoBin;$env:Path"
}
cargo build --release --manifest-path $SidecarManifest
if (-not (Test-Path $OutExe)) {
    throw "Sidecar build failed: $OutExe not found"
}
Copy-Item -Force $OutExe $Dest
Write-Host "-> $Dest" -ForegroundColor Green
