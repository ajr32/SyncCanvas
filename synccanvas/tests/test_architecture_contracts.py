"""Regression checks for family-scoped storage design and local migrations."""
import sqlite3
import pytest
from synccanvas import database
from synccanvas.firestore_design import COLLECTIONS, INDEXES, document_path


def test_firestore_family_scoped_design():
    assert "entries" in COLLECTIONS
    assert "family_id" in COLLECTIONS["entries"]
    assert document_path("family1", "entries", "task1") == "families/family1/entries/task1"
    assert ("entries", ("student_id", "class_id", "done", "due_date")) in INDEXES


@pytest.mark.parametrize("family,collection,doc", [
    ("", "entries", "one"),
    ("other/family", "entries", "one"),
    ("family", "entries", ".."),
    ("family", "unknown", "one"),
])
def test_firestore_rejects_unsafe_paths(family, collection, doc):
    with pytest.raises(ValueError):
        document_path(family, collection, doc)


def test_legacy_entries_migrate_without_data_loss(tmp_path, monkeypatch):
    path = tmp_path / "legacy.sqlite3"
    with sqlite3.connect(path) as conn:
        conn.executescript("""
        CREATE TABLE classes(id INTEGER PRIMARY KEY, name TEXT UNIQUE, sort_order INTEGER DEFAULT 0);
        INSERT INTO classes(id, name) VALUES(1, 'Math');
        CREATE TABLE entries(id INTEGER PRIMARY KEY, class_id INTEGER, kind TEXT, details TEXT, done INTEGER DEFAULT 0);
        INSERT INTO entries(id, class_id, kind, details, done) VALUES(1, 1, 'Homework', 'Keep me', 1);
        """)
    monkeypatch.setattr(database, "DB_PATH", path)
    for _ in range(2):
        with database.db() as conn:
            row = conn.execute("SELECT details, done, due_date, due_time, priority, progress FROM entries WHERE id=1").fetchone()
            assert row["details"] == "Keep me"
            assert row["done"] == 1
            assert row["due_date"] is None
            assert row["priority"] == "normal"
            assert row["progress"] == "done"
