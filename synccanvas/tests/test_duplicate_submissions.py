"""Duplicate form submissions must not create duplicate tasks."""
import re
from fastapi.testclient import TestClient
from synccanvas import database
from synccanvas.main import app

def test_repeated_submission_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "duplicate.sqlite3")
    with database.db() as conn:
        conn.execute("INSERT INTO classes(id,name) VALUES(1,'Math')")
    client = TestClient(app)
    html = client.get("/").text
    tokens = re.findall(r'name="submission_token" value="([0-9a-f]{64})"', html)
    assert tokens
    token = tokens[0]
    payload = {"kind": "Homework", "details": "Questions 1-10", "submission_token": token}
    first = client.post("/classes/1/entries", data=payload, follow_redirects=False)
    second = client.post("/classes/1/entries", data=payload, follow_redirects=False)
    assert first.status_code == second.status_code == 303
    with database.db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM entries").fetchone()[0] == 1
    payload["submission_token"] = "a" * 64 if token != "a" * 64 else "b" * 64
    assert client.post("/classes/1/entries", data=payload, follow_redirects=False).status_code == 303
    with database.db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM entries").fetchone()[0] == 2

def test_bad_token_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "bad-token.sqlite3")
    with database.db() as conn:
        conn.execute("INSERT INTO classes(id,name) VALUES(1,'Math')")
    response = TestClient(app).post("/classes/1/entries", data={
        "kind": "Homework", "details": "Questions 1-10", "submission_token": "invalid"
    })
    assert response.status_code == 422
    with database.db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM entries").fetchone()[0] == 0
