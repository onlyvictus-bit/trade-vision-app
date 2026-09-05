param(
    [int]$ApiPort = 8000,
    [int]$KronosPort = 8010,
    [int]$AdapterPort = 8011,
    [int]$WebPort = 8765
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path (Split-Path -Parent $root) ".venv\Scripts\python.exe"
$kronosPython = Join-Path $root "apps\kronos-service\.venv\Scripts\python.exe"
$pidFile = Join-Path $root "data\research-stack-pids.json"

if (-not (Test-Path $python)) {
    throw "Python runtime not found: $python"
}
if (-not (Test-Path $kronosPython)) {
    throw "Kronos Python runtime not found: $kronosPython"
}
if (-not $env:TRADEVISION_ADAPTER_SHARED_SECRET) {
    throw "TRADEVISION_ADAPTER_SHARED_SECRET is required."
}
if (-not $env:TRADEVISION_OPENALGO_ADAPTER_URL) {
    $env:TRADEVISION_OPENALGO_ADAPTER_URL = "http://127.0.0.1:$AdapterPort"
}
if (-not $env:TRADEVISION_KRONOS_SERVICE_URL) {
    $env:TRADEVISION_KRONOS_SERVICE_URL = "http://127.0.0.1:$KronosPort"
}
if (-not $env:TRADEVISION_ADAPTER_ALLOWED_HOSTS) {
    $env:TRADEVISION_ADAPTER_ALLOWED_HOSTS = "127.0.0.1,localhost"
}

foreach ($port in @($ApiPort, $KronosPort, $AdapterPort, $WebPort)) {
    if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
        throw "Port $port is already in use."
    }
}

$kronos = Start-Process -FilePath $kronosPython `
    -ArgumentList "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "$KronosPort" `
    -WorkingDirectory (Join-Path $root "apps\kronos-service") `
    -WindowStyle Hidden -PassThru

$adapter = Start-Process -FilePath $python `
    -ArgumentList "-m", "uvicorn", "adapter_app.main:app", "--host", "127.0.0.1", "--port", "$AdapterPort" `
    -WorkingDirectory (Join-Path $root "apps\openalgo-adapter") `
    -WindowStyle Hidden -PassThru

$api = Start-Process -FilePath $python `
    -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "$ApiPort" `
    -WorkingDirectory (Join-Path $root "apps\api") `
    -WindowStyle Hidden -PassThru

$preview = Start-Process -FilePath $python `
    -ArgumentList (Join-Path $root "scripts\serve_preview.py"), "--port", "$WebPort", "--api-base", "http://127.0.0.1:$ApiPort", "--directory", (Join-Path $root "apps\web\dist") `
    -WorkingDirectory $root `
    -WindowStyle Hidden -PassThru

$pidFileDirectory = Split-Path -Parent $pidFile
New-Item -ItemType Directory -Path $pidFileDirectory -Force | Out-Null
@{
    kronos = $kronos.Id
    adapter = $adapter.Id
    api = $api.Id
    preview = $preview.Id
    started_at = (Get-Date).ToUniversalTime().ToString("o")
} | ConvertTo-Json | Set-Content -LiteralPath $pidFile -Encoding UTF8

Write-Output "Trade Vision research stack started at http://127.0.0.1:$WebPort with real Kronos at http://127.0.0.1:$KronosPort"
