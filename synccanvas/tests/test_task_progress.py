"""Regression checks for manual-task progress states."""
from fastapi.testclient import TestClient
from synccanvas import database
from synccanvas.main import app

def test_task_progress_transitions(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "progress.sqlite3")
    with database.db() as conn:
        conn.execute("INSERT INTO classes(id,name) VALUES(1,'Math')")
        conn.execute("INSERT INTO entries(id,class_id,kind,details) VALUES(1,1,'Homework','Page 10')")
    client = TestClient(app)
    for progress, done in (("in_progress",0),("done",1),("not_started",0)):
        response = client.post("/entries/1/progress",data={"progress":progress},follow_redirects=False)
        assert response.status_code == 303
        with database.db() as conn:
            row=conn.execute("SELECT progress,done FROM entries WHERE id=1").fetchone()
            assert (row["progress"],row["done"]) == (progress,done)

def test_invalid_progress_does_not_change_task(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "invalid-progress.sqlite3")
    with database.db() as conn:
        conn.execute("INSERT INTO classes(id,name) VALUES(1,'Math')")
        conn.execute("INSERT INTO entries(id,class_id,kind,details) VALUES(1,1,'Homework','Page 10')")
    client=TestClient(app)
    assert client.post("/entries/1/progress",data={"progress":"unknown"}).status_code == 422
    assert client.post("/entries/999/progress",data={"progress":"done"}).status_code == 404
    with database.db() as conn:
        row=conn.execute("SELECT progress,done FROM entries WHERE id=1").fetchone()
        assert (row["progress"],row["done"]) == ("not_started",0)
