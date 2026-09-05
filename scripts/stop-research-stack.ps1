$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$pidFile = Join-Path $root "data\research-stack-pids.json"

if (-not (Test-Path $pidFile)) {
    Write-Output "No research stack PID file found."
    exit 0
}

$pids = Get-Content -LiteralPath $pidFile -Raw | ConvertFrom-Json
foreach ($name in @("preview", "api", "adapter", "kronos")) {
    $processId = $pids.$name
    if ($processId -and (Get-Process -Id $processId -ErrorAction SilentlyContinue)) {
        Stop-Process -Id $processId
        Wait-Process -Id $processId -Timeout 10 -ErrorAction SilentlyContinue
    }
}
Remove-Item -LiteralPath $pidFile -Force
Write-Output "Trade Vision research stack stopped."
