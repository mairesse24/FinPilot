$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw 'Project virtual environment missing. Follow README.md setup first.'
}
Push-Location -LiteralPath $projectRoot
try {
    & $pythonPath -m pytest tests -q
    if ($LASTEXITCODE -ne 0) { throw 'Intelligence tests failed' }
    git diff --check
    if ($LASTEXITCODE -ne 0) { throw 'Diff whitespace check failed' }
} finally {
    Pop-Location
}
