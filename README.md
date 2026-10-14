# SyncCanvas — local prototype

This is a **new application**. Keep the existing `CanvasSync/` folder unchanged. This prototype does not import it, call Canvas, or touch Google Calendar.

## Setup (Windows / PyCharm terminal)

From the SyncCanvas project root (where this pyproject.toml lives):

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
.\.venv\Scripts\python.exe -m uvicorn synccanvas.main:app --host 127.0.0.1 --port 8000 --reload
```

Open http://127.0.0.1:8000 for the student view and http://127.0.0.1:8000/parent for the parent preview. Both are visible to anyone who can reach the local server; **do not deploy or expose publicly**. Stop with Ctrl+C.

## Test

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Data is stored locally in `synccanvas_local.sqlite3`. No logins, shared-device access, verification workflow, or cloud persistence yet. Parent preview is not access-controlled. Do not enter sensitive student information until authentication and authorization are implemented.

## GitMap issue coverage

Prototype work toward 0.5.1.1.1 (FastAPI shell), 0.1.1.1.2 (simple task entry), 0.1.1.2.1 (parent preview), and 0.7.1.2.1 (basic class creation). These issues are **not closed**: remaining requirements include security, integration, full class management, and deployment checks.
