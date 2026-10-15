
"""SQLite storage for the SyncCanvas local prototype."""

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(
    os.environ.get(
        "SYNCCANVAS_DB",
        "synccanvas_local.sqlite3",
    )
)


@contextmanager
def db():
    DB_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")

    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS classes (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                sort_order INTEGER NOT NULL DEFAULT 0
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS entries (
                id INTEGER PRIMARY KEY,
                class_id INTEGER NOT NULL
                    REFERENCES classes(id),
                kind TEXT NOT NULL,
                details TEXT NOT NULL DEFAULT '',
                done INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS checkins (
                class_id INTEGER NOT NULL
                    REFERENCES classes(id),
                day TEXT NOT NULL,
                nothing_tonight INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY(class_id, day)
            )
        """)

        columns = {
            row["name"]
            for row in conn.execute(
                "PRAGMA table_info(entries)"
            )
        }

        if "parent_confirmed" not in columns:
            conn.execute("""
                ALTER TABLE entries
                ADD COLUMN parent_confirmed
                INTEGER NOT NULL DEFAULT 0
            """)

        if "coaching_note" not in columns:
            conn.execute("""
                ALTER TABLE entries
                ADD COLUMN coaching_note
                TEXT NOT NULL DEFAULT ''
            """)

        conn.commit()
        yield conn
        conn.commit()

    finally:
        conn.close()
