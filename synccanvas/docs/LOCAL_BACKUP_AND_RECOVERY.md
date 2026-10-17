# Local SQLite backup and recovery

**Not a production disaster-recovery guarantee.** First check the actual database path configured in `synccanvas/database.py` or environment variables.

1. Stop the app and any background sync writers.
2. Copy the configured SQLite file to a private location, with a dated filename.
3. Record the Git commit/app version and backup date.
4. Restart and check the app.

Example only, if the file really is named `synccanvas_local.sqlite3`:

```powershell
Copy-Item .\synccanvas_local.sqlite3 .\synccanvas_local.backup-2026-10-17.sqlite3
```

## Restore rehearsal
Use a separate test workspace and sample data. Stop writers, restore the backup **in the test workspace**, launch the app with the test DB, and check classes, local notes, reviews, and parent tasks. Never overwrite the live family DB merely to test restoration.

SQLite may use WAL sidecar files; copying a database while it is being written can be inconsistent. Stop all writers before the simple file-copy approach, or use SQLite's backup API for online backups. Keep real student data out of source control.
