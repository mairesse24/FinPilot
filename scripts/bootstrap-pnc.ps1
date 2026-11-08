$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$destination = Join-Path $projectRoot 'vendor/pnc-utd-hackathon-2026'
$revision = '55999aba3561270778f7830026bae666c5428740'
if (-not (Test-Path -LiteralPath $destination)) {
    git clone https://github.com/devfulcrum/pnc-utd-hackathon-2026.git $destination
    if ($LASTEXITCODE -ne 0) { throw 'PNC clone failed' }
}
git -C $destination checkout --detach $revision
if ($LASTEXITCODE -ne 0) { throw 'Could not check out pinned PNC revision' }
