param(
    [int]$ApiPort = 8000,
    [int]$KronosPort = 8010,
    [int]$AdapterPort = 8011,
    [int]$WebPort = 8765,
    [int]$TimeoutSeconds = 90,
    [int]$PollSeconds = 3,
    [string]$AdapterSharedSecret = ""
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path (Split-Path -Parent $root) ".venv\Scripts\python.exe"
$startScript = Join-Path $PSScriptRoot "start-research-stack.ps1"
$stopScript = Join-Path $PSScriptRoot "stop-research-stack.ps1"
$verifyScript = Join-Path $PSScriptRoot "verify_research_stack.py"

if (-not (Test-Path -LiteralPath $python)) {
    throw "Python runtime not found: $python"
}
foreach ($scriptPath in @($startScript, $stopScript, $verifyScript)) {
    if (-not (Test-Path -LiteralPath $scriptPath)) {
        throw "Required script not found: $scriptPath"
    }
}
if ($TimeoutSeconds -lt 10) {
    throw "TimeoutSeconds must be at least 10."
}
if ($PollSeconds -lt 1) {
    throw "PollSeconds must be at least 1."
}
if ($AdapterSharedSecret) {
    $env:TRADEVISION_ADAPTER_SHARED_SECRET = $AdapterSharedSecret
}
if (-not $env:TRADEVISION_ADAPTER_SHARED_SECRET) {
    throw "TRADEVISION_ADAPTER_SHARED_SECRET is required. This is a service identity secret, not a broker credential."
}

$apiBase = "http://127.0.0.1:$ApiPort"
$adapterUrl = "http://127.0.0.1:$AdapterPort"
$started = $false
$lastOutput = ""
$lastExitCode = 1

try {
    & $startScript -ApiPort $ApiPort -KronosPort $KronosPort -AdapterPort $AdapterPort -WebPort $WebPort
    if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) {
        throw "start-research-stack.ps1 exited with code $LASTEXITCODE"
    }
    $started = $true

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        $lastOutput = & $python $verifyScript --api-base $apiBase --adapter-url $adapterUrl
        $lastExitCode = $LASTEXITCODE
        if ($lastExitCode -eq 0) {
            $lastOutput | Write-Output
            exit 0
        }
        Start-Sleep -Seconds $PollSeconds
    }

    $lastOutput | Write-Output
    Write-Error "Research stack verification did not pass within $TimeoutSeconds seconds."
    exit 1
}
finally {
    if ($started) {
        & $stopScript
    }
}
