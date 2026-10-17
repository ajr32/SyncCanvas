"""Checks for fictional, isolated development seed data."""
import sqlite3

import pytest

from synccanvas import database
from synccanvas.seed_demo import create_demo


def test_demo_creates_fake_classes_and_tasks(tmp_path):
    target = tmp_path / "demo.sqlite3"
    assert create_demo(target) == target
    with sqlite3.connect(target) as conn:
        assert conn.execute("SELECT count(*) FROM classes").fetchone()[0] == 2
        assert conn.execute("SELECT count(*) FROM entries").fetchone()[0] == 2
    with pytest.raises(FileExistsError):
        create_demo(target)


def test_demo_refuses_live_database(tmp_path, monkeypatch):
    live = tmp_path / "family.sqlite3"
    monkeypatch.setattr(database, "DB_PATH", live)
    with pytest.raises(ValueError, match="family database"):
        create_demo(live)
    assert not live.exists()


def test_demo_rejects_missing_directory(tmp_path):
    with pytest.raises(ValueError, match="directory"):
        create_demo(tmp_path / "missing" / "demo.sqlite3")
