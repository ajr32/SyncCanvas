"""Tests for SyncCanvas issue #60: completion and reopening timestamps."""
from fastapi.testclient import TestClient
from synccanvas import database
from synccanvas.main import app


def setup_task(tmp_path, monkeypatch):
    monkeypatch.setattr(database, 'DB_PATH', tmp_path / 'timestamps.sqlite3')
    with database.db() as conn:
        conn.execute("INSERT INTO classes(id,name) VALUES(1,'Math')")
        conn.execute("INSERT INTO entries(id,class_id,kind,details) VALUES(1,1,'Homework','Page 10')")


def task():
    with database.db() as conn:
        return dict(conn.execute('SELECT done,progress,completed_at,parent_confirmed FROM entries WHERE id=1').fetchone())


def test_complete_reopen_complete_again(tmp_path, monkeypatch):
    setup_task(tmp_path, monkeypatch)
    client = TestClient(app)
    assert task()['completed_at'] is None
    assert client.post('/entries/1/progress', data={'progress':'done'}, follow_redirects=False).status_code == 303
    first = task()
    assert first['done'] == 1 and first['progress'] == 'done' and first['completed_at']
    assert client.post('/parent/entries/1/return', follow_redirects=False).status_code == 303
    reopened = task()
    assert reopened['done'] == 0 and reopened['progress'] == 'not_started' and reopened['completed_at'] is None
    assert client.post('/entries/1/progress', data={'progress':'done'}, follow_redirects=False).status_code == 303
    assert task()['completed_at'] is not None


def test_progress_and_legacy_done_endpoint(tmp_path, monkeypatch):
    setup_task(tmp_path, monkeypatch)
    client = TestClient(app)
    assert client.post('/entries/1/progress', data={'progress':'in_progress'}, follow_redirects=False).status_code == 303
    assert task()['completed_at'] is None
    assert client.post('/entries/1/done', follow_redirects=False).status_code == 303
    assert task()['completed_at']
    assert client.post('/entries/1/toggle', follow_redirects=False).status_code == 303
    assert task()['completed_at'] is None


def test_invalid_progress_keeps_timestamp(tmp_path, monkeypatch):
    setup_task(tmp_path, monkeypatch)
    client = TestClient(app)
    assert client.post('/entries/1/progress', data={'progress':'done'}, follow_redirects=False).status_code == 303
    before = task()
    assert client.post('/entries/1/progress', data={'progress':'invalid'}).status_code == 422
    assert task() == before
