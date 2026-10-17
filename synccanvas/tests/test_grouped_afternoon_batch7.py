from fastapi.testclient import TestClient
from synccanvas.main import app
from synccanvas.database import db


def test_linked_work_is_grouped_and_still_has_separate_progress(tmp_path, monkeypatch):
    import synccanvas.database as storage
    monkeypatch.setattr(storage, 'DB_PATH', tmp_path / 'group.sqlite3')
    client = TestClient(app)
    with db() as conn:
        conn.execute("INSERT INTO classes(id,name) VALUES (1,'Math')")
        conn.execute("INSERT INTO canvas_course_links(canvas_course_id,class_id) VALUES (100,1)")
        conn.execute("INSERT INTO canvas_assignments(id,canvas_course_id,canvas_assignment_id,title) VALUES (10,100,99,'Fractions')")
        conn.execute("INSERT INTO entries(id,class_id,kind,details) VALUES (5,1,'Homework','Finish worksheet')")
    client.post('/parent/entries/5/canvas-link',data={'canvas_assignment_id':10})
    html = client.get('/afternoon').text
    assert 'Related notes and tasks (1)' in html or 'Notes and tasks (1)' in html
    assert html.count('Finish worksheet') == 1
    assert '/entries/5/progress' in html
    assert html.index('Fractions') < html.index('Finish worksheet')


def test_unlinked_work_stays_visible(tmp_path, monkeypatch):
    import synccanvas.database as storage
    monkeypatch.setattr(storage, 'DB_PATH', tmp_path / 'unlinked.sqlite3')
    client = TestClient(app)
    with db() as conn:
        conn.execute("INSERT INTO classes(id,name) VALUES (1,'Math')")
        conn.execute("INSERT INTO entries(id,class_id,kind,details) VALUES (5,1,'Homework','Separate worksheet')")
    html = client.get('/afternoon').text
    assert html.count('Separate worksheet') == 1
    assert '/entries/5/progress' in html


def test_future_work_is_visible_but_not_on_today_list(tmp_path, monkeypatch):
    import synccanvas.database as storage
    monkeypatch.setattr(storage, 'DB_PATH', tmp_path / 'future.sqlite3')
    client = TestClient(app)
    with db() as conn:
        conn.execute("INSERT INTO classes(id,name) VALUES (1,'Math')")
        conn.execute("INSERT INTO entries(id,class_id,kind,details,planned_date) VALUES (5,1,'Study','Next week practice','2099-01-01')")
    html = client.get('/afternoon').text
    assert 'Planned for later (1)' in html
    assert html.count('Next week practice') == 1
    assert 'Work on January 1, 2099' in html
