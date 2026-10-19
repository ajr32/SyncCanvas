import importlib.util
from pathlib import Path
import sqlite3
import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "sqlite_backup.py"
spec = importlib.util.spec_from_file_location("sqlite_backup", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def sample(path):
    with sqlite3.connect(path) as c:
        c.execute("CREATE TABLE entries(id INTEGER PRIMARY KEY, title TEXT)")
        c.execute("INSERT INTO entries(title) VALUES ('Read chapter')")

def test_backup_and_restore_preserve_data(tmp_path):
    live = tmp_path / "live.sqlite3"
    sample(live)
    saved = module.backup(live, tmp_path / "backups")
    with sqlite3.connect(live) as c:
        c.execute("UPDATE entries SET title='Changed after backup'")
    restored = module.restore(saved, tmp_path / "restored.sqlite3")
    with sqlite3.connect(restored) as c:
        assert c.execute("SELECT title FROM entries").fetchone()[0] == "Read chapter"

def test_restore_never_overwrites(tmp_path):
    live = tmp_path / "live.sqlite3"
    sample(live)
    saved = module.backup(live, tmp_path / "backups")
    with pytest.raises(FileExistsError):
        module.restore(saved, live)

def test_missing_and_invalid_database(tmp_path):
    with pytest.raises(ValueError):
        module.backup(tmp_path / "missing.sqlite3", tmp_path / "backups")
    bad = tmp_path / "bad.sqlite3"
    bad.write_text("not a sqlite file")
    with pytest.raises(sqlite3.DatabaseError):
        module.check_database(bad)

def test_rotation_and_keep_boundary(tmp_path):
    live = tmp_path / "live.sqlite3"
    sample(live)
    for _ in range(3):
        module.backup(live, tmp_path / "backups", keep=2)
    assert len(list((tmp_path / "backups").glob("synccanvas-*.sqlite3"))) == 2
    with pytest.raises(ValueError):
        module.backup(live, tmp_path / "backups", keep=0)

def test_restore_rejects_invalid_backup(tmp_path):
    invalid = tmp_path / "bad.sqlite3"
    invalid.write_text("invalid")
    with pytest.raises(sqlite3.DatabaseError):
        module.restore(invalid, tmp_path / "restored.sqlite3")
    assert not (tmp_path / "restored.sqlite3").exists()
