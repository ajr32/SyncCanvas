import pytest
from fastapi.testclient import TestClient
from synccanvas import main


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "DB_PATH", tmp_path / "test.sqlite3")
    return TestClient(main.app)


def test_student_to_parent_flow(client):
    assert client.get("/").status_code == 200
    assert client.post("/classes", data={"name": "Math"}).status_code == 200
    assert client.post("/classes/1/entries", data={"kind": "Homework", "details": "Page 12"}).status_code == 200
    parent = client.get("/parent").text
    assert "Math" in parent and "Page 12" in parent and "Open" in parent
    client.post("/entries/1/toggle")
    assert "Done" in client.get("/parent").text


def test_invalid_and_missing_class(client):
    client.post("/classes", data={"name": "Science"})
    assert client.post("/classes/1/entries", data={"kind": "Not a real type"}).status_code == 422
    assert client.post("/classes/99/entries", data={"kind": "Study"}).status_code == 404
    assert client.post("/classes", data={"name": "  "}).status_code == 422


def test_html_is_escaped(client):
    client.post("/classes", data={"name": "<script>alert(1)</script>"})
    page = client.get("/").text
    assert "&lt;script&gt;" in page
    assert "<script>alert(1)</script>" not in page
