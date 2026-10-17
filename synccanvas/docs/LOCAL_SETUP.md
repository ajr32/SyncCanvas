# Local setup and operation

SyncCanvas is currently a **local, unauthenticated prototype**. Do not expose it on a public interface or school network.

## Run
From the project root with Python 3.11+:

```powershell
python -m pip install -e ".[test]"
python -m uvicorn synccanvas.main:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000/ and stop with Ctrl+C. If dependencies are already installed, only the second command is needed.

## Pages
- `/` — My Classes
- `/add` — Add Information
- `/review` — School Check-Out
- `/afternoon` — My Afternoon
- `/parent` — Parent Review
- `/settings` — Settings
- `/parent/classes` — class management
- `/parent/schedule` — bell schedule

## First-run check
Confirm active classes in Settings, add a disposable local note, see it in My Afternoon, and check the parent view. Run `python -m pytest -q`. A successful local launch is **not** production readiness.
