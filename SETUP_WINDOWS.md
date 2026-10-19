# SyncCanvas — Windows setup

From the project root in PowerShell, first-time setup:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
.\scripts\lock-dependencies.ps1
```

The lock script creates `requirements-lock.txt` from the exact packages
installed in your tested Windows environment. Review and commit this file.
It is **not included** until you generate it locally; don't mistake
`pyproject.toml`'s version ranges for a lock.

For subsequent installs:

```powershell
.\scripts\setup-windows.ps1
.\.venv\Scripts\python.exe -m uvicorn synccanvas.main:app --host 127.0.0.1 --port 8000
```

Copy `.env.example` to `.env`, then set the real Canvas URL and token.
Use HTTPS; provide both values together. Keep `.env` private.
Run tests with `.\.venv\Scripts\python.exe -m pytest -q`.

The parent view is not authenticated. Do not expose this server publicly.
