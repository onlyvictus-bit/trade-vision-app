$ErrorActionPreference = "Stop"
$Root = Resolve-Path "$PSScriptRoot\.."
Set-Location $Root
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Python)) {
    $Python = Join-Path (Resolve-Path "$Root\..") ".venv\Scripts\python.exe"
}
if (-not (Test-Path -LiteralPath $Python)) {
    throw "No Python virtual environment found. Create one in trade-vision-app\.venv or stock-app\.venv."
}
$env:PYTHONPATH = Join-Path $Root "apps\api"
& $Python -m uvicorn app.main:app --reload --app-dir apps\api --host 127.0.0.1 --port 8000
