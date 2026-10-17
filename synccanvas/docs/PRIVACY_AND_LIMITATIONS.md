# Privacy and current limitations

SyncCanvas is a local FastAPI/SQLite prototype. The current UI explicitly states that separate student, parent, and school staff accounts are **not enforced**. Review records do not authenticate who made them.

## Do now
- Bind the app to `127.0.0.1` only.
- Avoid unnecessary sensitive student details in notes and screenshots.
- Never commit Canvas tokens, `.env` secrets, or real-data SQLite files.
- Use synthetic data for demos and GitHub issue reproduction.
- Keep backups private.

## Keep open in GitMap
Role-based authentication, verified staff identity, school Chromebook access/approval, secure hosting, retention/deletion policy, production backup/recovery, and actual family acceptance testing. A working local form does not close these issues.
