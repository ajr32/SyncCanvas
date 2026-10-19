"""Parent-accessible Canvas update controls and safe return navigation."""
from fastapi.testclient import TestClient
from synccanvas.main import app
from synccanvas.models.sync_result import SyncResult, SyncState
from synccanvas.services.sync_coordinator import sync_coordinator


def test_parent_and_settings_show_sync_controls(monkeypatch, tmp_path):
    from synccanvas import database
    monkeypatch.setattr(database, 'DB_PATH', tmp_path / 'sync.sqlite3')
    monkeypatch.setattr(sync_coordinator, 'status', lambda: SyncResult(state=SyncState.IDLE, message='Ready to synchronize.'))
    client = TestClient(app)
    for path in ('/parent', '/settings'):
        response = client.get(path)
        assert response.status_code == 200
        assert 'action="/sync/run"' in response.text
        assert f'name="return_to" value="{path}"' in response.text
        assert 'Check for updates' in response.text


def test_sync_returns_to_origin_and_blocks_external_redirect(monkeypatch):
    calls = []
    monkeypatch.setattr(sync_coordinator, 'request_sync', lambda: calls.append(True))
    client = TestClient(app)
    for target, expected in [('/parent', '/parent'), ('/settings', '/settings'), ('https://evil.example', '/'), ('//evil.example', '/')]:
        response = client.post('/sync/run', data={'return_to': target}, follow_redirects=False)
        assert response.status_code == 303
        assert response.headers['location'] == expected
    assert len(calls) == 4


def test_running_sync_shows_progress_without_duplicate_button(monkeypatch, tmp_path):
    from synccanvas import database
    monkeypatch.setattr(database, 'DB_PATH', tmp_path / 'sync.sqlite3')
    monkeypatch.setattr(sync_coordinator, 'status', lambda: SyncResult(state=SyncState.RUNNING, message='Synchronization is running.'))
    response = TestClient(app).get('/settings')
    assert response.status_code == 200
    assert 'Checking Canvas now' in response.text
    assert 'action="/sync/run"' not in response.text
