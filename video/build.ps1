$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$videoPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $videoPython)) {
    throw 'Create video/.venv and install video/requirements.txt first; see video/README.md.'
}
Push-Location -LiteralPath $projectRoot
try {
    & $videoPython -m manim -qh --fps 30 --media_dir video/media video/scenes.py RMSIntegrationFilm
    if ($LASTEXITCODE -ne 0) { throw 'Manim rendering failed.' }
    & $videoPython video/finalize.py
    if ($LASTEXITCODE -ne 0) { throw 'Finalization/audit failed.' }
} finally {
    Pop-Location
}
