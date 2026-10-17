from fastapi.testclient import TestClient
from synccanvas.main import app
from synccanvas.database import db


def test_parent_can_link_and_unlink_without_merging(tmp_path, monkeypatch):
    import synccanvas.database as storage
    monkeypatch.setattr(storage, 'DB_PATH', tmp_path / 'links.sqlite3')
    client = TestClient(app)
    with db() as conn:
        conn.execute("INSERT INTO classes(id,name) VALUES (1,'Math')")
        conn.execute("INSERT INTO canvas_course_links(canvas_course_id,class_id) VALUES (100,1)")
        conn.execute("INSERT INTO canvas_assignments(id,canvas_course_id,canvas_assignment_id,title) VALUES (10,100,99,'Fractions')")
        conn.execute("INSERT INTO entries(id,class_id,kind,details) VALUES (5,1,'Homework','Finish worksheet')")
    r=client.post('/parent/entries/5/canvas-link',data={'canvas_assignment_id':10},follow_redirects=False)
    assert r.status_code==303
    assert 'Related Canvas: Fractions' in client.get('/afternoon').text
    assert 'Remove Canvas link' in client.get('/parent').text
    assert client.post('/parent/entries/5/canvas-unlink').status_code==200
    with db() as conn:
        assert conn.execute('SELECT count(*) FROM entry_canvas_links').fetchone()[0]==0
        assert conn.execute('SELECT count(*) FROM entries').fetchone()[0]==1
        assert conn.execute('SELECT count(*) FROM canvas_assignments').fetchone()[0]==1


def test_parent_cannot_link_different_class(tmp_path, monkeypatch):
    import synccanvas.database as storage
    monkeypatch.setattr(storage, 'DB_PATH', tmp_path / 'cross.sqlite3')
    client=TestClient(app)
    with db() as conn:
        conn.execute("INSERT INTO classes(id,name) VALUES (1,'Math'),(2,'Science')")
        conn.execute("INSERT INTO canvas_course_links(canvas_course_id,class_id) VALUES (200,2)")
        conn.execute("INSERT INTO canvas_assignments(id,canvas_course_id,canvas_assignment_id,title) VALUES (10,200,99,'Lab')")
        conn.execute("INSERT INTO entries(id,class_id,kind,details) VALUES (5,1,'Homework','Math practice')")
    assert client.post('/parent/entries/5/canvas-link',data={'canvas_assignment_id':10}).status_code==422
    with db() as conn:
        assert conn.execute('SELECT count(*) FROM entry_canvas_links').fetchone()[0]==0


def test_missing_entry_cannot_link(tmp_path, monkeypatch):
    import synccanvas.database as storage
    monkeypatch.setattr(storage, 'DB_PATH', tmp_path / 'missing.sqlite3')
    client=TestClient(app)
    assert client.post('/parent/entries/999/canvas-link',data={'canvas_assignment_id':1}).status_code==404
