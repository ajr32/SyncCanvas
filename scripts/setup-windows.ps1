$ErrorActionPreference = "Stop"
if (-not (Test-Path "pyproject.toml")) { throw "Run from SyncCanvas project root" }
if (-not (Test-Path ".venv\Scripts\python.exe")) { py -3.11 -m venv .venv }
$python = ".\.venv\Scripts\python.exe"
if (-not (Test-Path "requirements-lock.txt")) { throw "Create requirements-lock.txt first (see SETUP_WINDOWS.md)" }
& $python -m pip install -r requirements-lock.txt
if ($LASTEXITCODE -ne 0) { throw "Locked dependency installation failed" }
& $python -m pip install --no-deps -e .
if ($LASTEXITCODE -ne 0) { throw "Project installation failed" }
& $python -m pytest -q
if ($LASTEXITCODE -ne 0) { throw "Tests failed" }
