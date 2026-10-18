"""Ensure core student/parent pages work without client-side JavaScript."""
from fastapi.testclient import TestClient
from synccanvas.main import app
from synccanvas import database
from synccanvas import pages


def test_server_rendered_pages_are_accessible_without_javascript(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "accessibility.sqlite3")
    monkeypatch.setattr(pages, "db", database.db)
    with TestClient(app) as client:
        for path in ("/", "/parent"):
            response = client.get(path)
            assert response.status_code == 200
            text = response.text.lower()
            assert '<html lang="en">' in text
            assert '<main>' in text
            assert '<nav>' in text
            assert '<title>' in text
            assert '<meta name="viewport"' in text
            assert 'type="module"' not in text
