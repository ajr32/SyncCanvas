$ErrorActionPreference = "Stop"
$python = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $python)) { throw "Create .venv first: py -3.11 -m venv .venv" }
& $python -m pip freeze --exclude-editable | Set-Content -Encoding utf8 requirements-lock.txt
if ($LASTEXITCODE -ne 0) { throw "Failed to generate lock" }
Write-Host "Review and commit requirements-lock.txt"
