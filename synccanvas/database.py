
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

    if "origin" not in columns:
        conn.execute(
            "ALTER TABLE entries ADD COLUMN "
            "origin TEXT NOT NULL DEFAULT 'student'"
        )

    if "planned_date" not in columns:
        conn.execute(
            "ALTER TABLE entries ADD COLUMN planned_date TEXT"
        )

    # Issue #61: optional manual task deadlines and priority.
    # Existing rows are preserved; missing deadlines stay NULL.
    if "due_date" not in columns:
        conn.execute(
            "ALTER TABLE entries ADD COLUMN due_date TEXT"
        )

    if "due_time" not in columns:
        conn.execute(
            "ALTER TABLE entries ADD COLUMN due_time TEXT"
        )

    if "priority" not in columns:
        conn.execute(
            "ALTER TABLE entries ADD COLUMN "
            "priority TEXT NOT NULL DEFAULT 'normal'"
        )

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

    if "submission_token" not in columns:
        conn.execute(
            "ALTER TABLE entries ADD COLUMN submission_token TEXT"
        )

    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS "
        "idx_entries_submission_token "
        "ON entries(submission_token)"
    )

    if "completed_at" not in columns:
        conn.execute(
            "ALTER TABLE entries ADD COLUMN completed_at TEXT"
        )
        # Legacy completed tasks have no reliable completion time.

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
            CREATE TABLE IF NOT EXISTS bell_periods (
                id INTEGER PRIMARY KEY,
                label TEXT NOT NULL UNIQUE,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                weekdays TEXT NOT NULL DEFAULT '01234'
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS school_days (
                day TEXT PRIMARY KEY,
                kind TEXT NOT NULL
                    CHECK(kind IN ('closed','shortened')),
                note TEXT NOT NULL DEFAULT ''
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS school_day_periods (
                day TEXT NOT NULL
                    REFERENCES school_days(day) ON DELETE CASCADE,
                period_id INTEGER NOT NULL
                    REFERENCES bell_periods(id) ON DELETE CASCADE,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                PRIMARY KEY(day, period_id)
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS class_periods (
                class_id INTEGER NOT NULL
                    REFERENCES classes(id) ON DELETE CASCADE,
                period_id INTEGER NOT NULL
                    REFERENCES bell_periods(id) ON DELETE CASCADE,
                PRIMARY KEY(class_id, period_id)
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS lunch_buddies (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                period_id INTEGER NOT NULL
                    REFERENCES bell_periods(id) ON DELETE CASCADE,
                weekdays TEXT NOT NULL DEFAULT '01234'
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS lunch_tasks (
                id INTEGER PRIMARY KEY,
                activity_id INTEGER NOT NULL
                    REFERENCES lunch_buddies(id) ON DELETE CASCADE,
                details TEXT NOT NULL,
                done INTEGER NOT NULL DEFAULT 0,
                parent_confirmed INTEGER NOT NULL DEFAULT 0,
                coaching_note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

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

        # Persistent per-class materials, independent of today's packing status.
        conn.execute("""CREATE TABLE IF NOT EXISTS class_materials (
            id INTEGER PRIMARY KEY,
            class_id INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
            description TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(class_id, description)
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS material_packing (
            material_id INTEGER NOT NULL REFERENCES class_materials(id) ON DELETE CASCADE,
            day TEXT NOT NULL,
            packed INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(material_id, day)
        )""")

        ensure_entry_columns(conn)

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS recurring_expectations (
                id INTEGER PRIMARY KEY,
                class_id INTEGER NOT NULL REFERENCES classes(id),
                kind TEXT NOT NULL,
                details TEXT NOT NULL,
                frequency TEXT NOT NULL
                    CHECK(frequency IN ('daily','weekdays')),
                enabled INTEGER NOT NULL DEFAULT 1
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS recurring_instances (
                expectation_id INTEGER NOT NULL
                    REFERENCES recurring_expectations(id),
                work_date TEXT NOT NULL,
                entry_id INTEGER NOT NULL REFERENCES entries(id),
                PRIMARY KEY(expectation_id,work_date)
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS school_reviews (
                class_id INTEGER NOT NULL
                    REFERENCES classes(id) ON DELETE CASCADE,
                day TEXT NOT NULL,
                reviewed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                outcome TEXT NOT NULL
                    CHECK(outcome IN (
                        'reviewed','nothing','needs_followup'
                    )),
                PRIMARY KEY(class_id,day)
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS paper_reviews (
                day TEXT PRIMARY KEY,
                pocket_checked INTEGER NOT NULL DEFAULT 0,
                backpack_checked INTEGER NOT NULL DEFAULT 0,
                notes TEXT NOT NULL DEFAULT '',
                reviewed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS class_questions (
                class_id INTEGER NOT NULL
                    REFERENCES classes(id) ON DELETE CASCADE,
                day TEXT NOT NULL,
                question TEXT NOT NULL,
                resolved INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(class_id,day)
            )
            """
        )

        # End-of-day packing and follow-up records; no staff authentication implied.
        conn.execute("""CREATE TABLE IF NOT EXISTS checkout_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day TEXT NOT NULL,
            item_type TEXT NOT NULL CHECK(item_type IN ('book','paper','device','other')),
            description TEXT NOT NULL,
            ready INTEGER NOT NULL DEFAULT 0,
            UNIQUE(day,item_type,description)
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS checkout_followups (
            class_id INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
            day TEXT NOT NULL,
            resolution TEXT NOT NULL DEFAULT 'pending'
                CHECK(resolution IN ('pending','resolved','exception')),
            note TEXT NOT NULL DEFAULT '',
            PRIMARY KEY(class_id,day)
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS checkout_corrections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_id INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
            day TEXT NOT NULL,
            previous_outcome TEXT,
            new_outcome TEXT NOT NULL,
            corrected_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")
        conn.execute("""CREATE INDEX IF NOT EXISTS idx_checkout_corrections_class_day
            ON checkout_corrections(class_id,day)""")
        review_columns = {r['name'] for r in conn.execute('PRAGMA table_info(school_reviews)')}
        if 'reviewed_by' not in review_columns:
            conn.execute("ALTER TABLE school_reviews ADD COLUMN reviewed_by TEXT NOT NULL DEFAULT 'unspecified'")

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

        # Official Canvas assignment deadlines remain separate.
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
        if "last_seen_at" not in columns:
            conn.execute("ALTER TABLE canvas_assignments ADD COLUMN last_seen_at TEXT")
        if "missing_from_canvas" not in columns:
            conn.execute("ALTER TABLE canvas_assignments ADD COLUMN missing_from_canvas INTEGER NOT NULL DEFAULT 0")
        conn.execute("""CREATE TABLE IF NOT EXISTS canvas_sync_audit (
            id INTEGER PRIMARY KEY CHECK (id=1),
            last_success_at TEXT NOT NULL
        )""")
        if "family_category" not in columns:
            conn.execute("ALTER TABLE canvas_assignments ADD COLUMN family_category TEXT NOT NULL DEFAULT 'auto'")

        if "canvas_missing" not in columns:
            conn.execute("ALTER TABLE canvas_assignments ADD COLUMN canvas_missing INTEGER NOT NULL DEFAULT 0")
        if "canvas_submitted" not in columns:
            conn.execute("ALTER TABLE canvas_assignments ADD COLUMN canvas_submitted INTEGER NOT NULL DEFAULT 0")
        if "review_dismissed" not in columns:
            conn.execute("ALTER TABLE canvas_assignments ADD COLUMN review_dismissed INTEGER NOT NULL DEFAULT 0")

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

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS entry_canvas_links (
                entry_id INTEGER PRIMARY KEY
                    REFERENCES entries(id) ON DELETE CASCADE,
                canvas_assignment_id INTEGER NOT NULL
                    REFERENCES canvas_assignments(id) ON DELETE CASCADE
            )
            """
        )

        conn.commit()
        yield conn
        conn.commit()

    finally:
        conn.close()
