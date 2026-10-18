"""Issue #24: core form workflow works without JavaScript."""
import re

import pytest
from fastapi.testclient import TestClient
from synccanvas import database, main


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "family.sqlite3")
    with TestClient(main.app) as test_client:
        yield test_client


def test_quick_add_form_is_usable_without_javascript(client):
    client.post("/classes", data={"name": "Math"})
    client.post("/classes", data={"name": "Science"})
    page = client.get("/add")
    assert page.status_code == 200
    assert '<form id="quick-entry" method="post" action="/add">' in page.text
    assert 'name="class_id"' in page.text
    assert 'name="kind"' in page.text
    assert 'name="details"' in page.text
    assert 'type="submit"' in page.text
    assert 'addEventListener' not in page.text
    token = re.search(r'name="submission_token" value="([0-9a-f]{64})"', page.text).group(1)
    response = client.post("/add", data={"class_id": 2, "kind": "Homework", "details": "Science worksheet", "submission_token": token}, follow_redirects=False)
    assert response.status_code == 303
    with database.db() as conn:
        task = conn.execute("SELECT class_id,details FROM entries").fetchone()
        assert task["class_id"] == 2
        assert task["details"] == "Science worksheet"


def test_quick_add_rejects_invalid_class_and_invalid_content(client):
    client.post("/classes", data={"name": "Math"})
    assert client.post("/add", data={"class_id": 999, "kind": "Homework", "details": "Page 4"}).status_code == 404
    assert client.post("/add", data={"class_id": 1, "kind": "Homework", "details": "   "}).status_code == 422
    assert client.post("/add", data={"class_id": "not-a-number", "kind": "Homework", "details": "Page 4"}).status_code == 422
    with database.db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM entries").fetchone()[0] == 0


def test_quick_add_duplicate_post_does_not_duplicate_entry(client):
    client.post("/classes", data={"name": "Math"})
    data = {"class_id": 1, "kind": "Homework", "details": "Page 7", "submission_token": "a" * 64}
    assert client.post("/add", data=data, follow_redirects=False).status_code == 303
    assert client.post("/add", data=data, follow_redirects=False).status_code == 303
    with database.db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM entries").fetchone()[0] == 1
