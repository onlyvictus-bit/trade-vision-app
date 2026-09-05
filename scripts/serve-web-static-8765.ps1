$ErrorActionPreference = "Stop"

$root = Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")
$dist = Join-Path $root "apps\web\dist"
$python = Join-Path $root ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $dist)) {
    throw "Frontend dist folder not found at $dist. Run npm run build first."
}

if (-not (Test-Path -LiteralPath $python)) {
    $python = "python"
}

Write-Host "Serving Trade Vision static frontend on http://127.0.0.1:8765"
Write-Host "Proxying same-origin API requests to http://127.0.0.1:8000"
& $python (Join-Path $PSScriptRoot "serve_preview.py") --host 127.0.0.1 --port 8765 --api-base http://127.0.0.1:8000 --directory $dist
