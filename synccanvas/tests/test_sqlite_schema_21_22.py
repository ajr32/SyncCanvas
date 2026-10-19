"""#21/#22: live SQLite schema and non-destructive upgrades (no Firestore dependency)."""
import sqlite3
from synccanvas import database


def test_fresh_schema_has_required_relations_and_indexes(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "fresh.sqlite3")
    with database.db() as conn:
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        assert {"classes", "entries", "canvas_assignments", "entry_canvas_links",
                "school_reviews", "canvas_course_links"} <= tables
        indexes = {r[1] for r in conn.execute("PRAGMA index_list(canvas_assignments)")}
        assert "idx_canvas_assignments_course" in indexes
        entry_indexes = {r[1] for r in conn.execute("PRAGMA index_list(entries)")}
        assert "idx_entries_submission_token" in entry_indexes
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []


def test_legacy_upgrade_is_repeatable_and_preserves_user_work(tmp_path, monkeypatch):
    path = tmp_path / "legacy.sqlite3"
    with sqlite3.connect(path) as conn:
        conn.executescript("""
            CREATE TABLE classes (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE,
                                  sort_order INTEGER NOT NULL DEFAULT 0);
            INSERT INTO classes(id, name) VALUES(1, 'ELA');
            CREATE TABLE entries (id INTEGER PRIMARY KEY, class_id INTEGER NOT NULL,
                                  kind TEXT NOT NULL, details TEXT NOT NULL DEFAULT '',
                                  done INTEGER NOT NULL DEFAULT 0,
                                  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
            INSERT INTO entries(id,class_id,kind,details,done)
                VALUES(8,1,'Homework','Keep my essay',1);
        """)
    monkeypatch.setattr(database, "DB_PATH", path)
    for _ in range(3):
        with database.db() as conn:
            row = conn.execute(
                "SELECT id, details, done, progress FROM entries WHERE id=8").fetchone()
            assert tuple(row) == (8, "Keep my essay", 1, "done")
            assert conn.execute("SELECT COUNT(*) FROM entries").fetchone()[0] == 1
            assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_foreign_keys_are_enforced(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "keys.sqlite3")
    with database.db() as conn:
        import pytest
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO entries(class_id,kind,details) VALUES (999,'Homework','Bad link')")
        conn.rollback()
