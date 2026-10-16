
"""SQLite storage for the SyncCanvas local prototype."""

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(
    os.environ.get("SYNCCANVAS_DB", "synccanvas_local.sqlite3")
)


def ensure_class_columns(conn):
    columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(classes)")
    }

    if "enabled" not in columns:
        conn.execute(
            "ALTER TABLE classes ADD COLUMN "
            "enabled INTEGER NOT NULL DEFAULT 1"
        )

    if "archived" not in columns:
        conn.execute(
            "ALTER TABLE classes ADD COLUMN "
            "archived INTEGER NOT NULL DEFAULT 0"
        )


def ensure_entry_columns(conn):
    columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(entries)")
    }

    if "parent_confirmed" not in columns:
        conn.execute(
            "ALTER TABLE entries ADD COLUMN "
            "parent_confirmed INTEGER NOT NULL DEFAULT 0"
        )

    if "coaching_note" not in columns:
        conn.execute(
            "ALTER TABLE entries ADD COLUMN "
            "coaching_note TEXT NOT NULL DEFAULT ''"
        )

    if "progress" not in columns:
        conn.execute(
            "ALTER TABLE entries ADD COLUMN "
            "progress TEXT NOT NULL DEFAULT 'not_started'"
        )

        # Preserve completion status for existing tasks.
        conn.execute(
            """
            UPDATE entries
            SET progress = 'done'
            WHERE done = 1
            """
        )


@contextmanager
def db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")

    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS classes (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                sort_order INTEGER NOT NULL DEFAULT 0
            )
            """
        )

        ensure_class_columns(conn)

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS entries (
                id INTEGER PRIMARY KEY,
                class_id INTEGER NOT NULL REFERENCES classes(id),
                kind TEXT NOT NULL,
                details TEXT NOT NULL DEFAULT '',
                done INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        ensure_entry_columns(conn)

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS checkins (
                class_id INTEGER NOT NULL REFERENCES classes(id),
                day TEXT NOT NULL,
                nothing_tonight INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY(class_id, day)
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS canvas_course_links (
                canvas_course_id INTEGER PRIMARY KEY,
                class_id INTEGER NOT NULL UNIQUE
                    REFERENCES classes(id) ON DELETE CASCADE
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS canvas_assignments (
                id INTEGER PRIMARY KEY,
                canvas_course_id INTEGER NOT NULL,
                canvas_assignment_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                due_at TEXT,
                due_date TEXT,
                html_url TEXT,
                student_notes TEXT NOT NULL DEFAULT '',
                completed INTEGER NOT NULL DEFAULT 0,
                submission_types TEXT NOT NULL DEFAULT '[]',
                UNIQUE(canvas_course_id, canvas_assignment_id)
            )
            """
        )

        columns = {
            row["name"]
            for row in conn.execute(
                "PRAGMA table_info(canvas_assignments)"
            )
        }

        if "submission_types" not in columns:
            conn.execute(
                "ALTER TABLE canvas_assignments ADD COLUMN "
                "submission_types TEXT NOT NULL DEFAULT '[]'"
            )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_canvas_assignments_course
            ON canvas_assignments(canvas_course_id)
            """
        )

        conn.commit()
        yield conn
        conn.commit()

    finally:
        conn.close()
