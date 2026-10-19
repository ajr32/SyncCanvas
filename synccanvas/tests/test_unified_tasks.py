from fastapi.testclient import TestClient
from synccanvas.database import db
from synccanvas.main import app


def setup(tmp_path, monkeypatch):
    import synccanvas.database as storage
    monkeypatch.setattr(storage, 'DB_PATH', tmp_path / 'unified.sqlite3')
    with db() as conn:
        conn.execute("INSERT INTO classes(id,name) VALUES (1,'ELA')")
        conn.execute("INSERT INTO canvas_course_links(canvas_course_id,class_id) VALUES (10,1)")
        for aid,title,due,types in (
            (1,'Subject and Predicate Quiz','2026-10-20','["external_tool"]'),
            (2,'Unit 2 Answer Key','2026-10-11','["none"]'),
            (3,'Warmups 10/18-10/22',None,'["none"]'),
            (4,'Essay Draft','2026-10-19','["online_upload"]'),
            (5,'Mystery item',None,'[]')):
            conn.execute("""INSERT INTO canvas_assignments(id,canvas_course_id,canvas_assignment_id,title,due_date,submission_types)
                VALUES (?,?,?,?,?,?)""",(aid,10,aid,title,due,types))
        conn.execute("INSERT INTO entries(id,class_id,kind,details) VALUES (20,1,'Study','Read chapter')")
    return TestClient(app)


def test_groups_and_parent_overrides(tmp_path,monkeypatch):
    client=setup(tmp_path,monkeypatch)
    page=client.get('/afternoon').text
    assert page.index('Read chapter') < page.index('Essay Draft')
    assert 'Upcoming assessments' in page
    assert 'Review and reference' in page
    assert 'In-class information' in page
    assert 'Unsorted Canvas items' in page
    assert 'Overdue · October 11' not in page
    assert client.post('/parent/canvas/4/category',data={'category':'review'}).status_code==200
    with db() as conn:
        assert conn.execute('SELECT family_category FROM canvas_assignments WHERE id=4').fetchone()[0]=='review'
    assert client.post('/parent/canvas/4/category',data={'category':'nonsense'}).status_code==422


def test_promote_link_and_prevent_duplicate(tmp_path,monkeypatch):
    client=setup(tmp_path,monkeypatch)
    for _ in range(2):
        assert client.post('/parent/canvas/1/add-task',data={'kind':'Study'}).status_code==200
    with db() as conn:
        assert conn.execute('SELECT count(*) FROM entry_canvas_links WHERE canvas_assignment_id=1').fetchone()[0]==1
    page=client.get('/afternoon').text
    assert 'Study for Subject and Predicate Quiz' in page
    assert 'Related Canvas: Subject and Predicate Quiz' in page
    assert client.post('/parent/canvas/1/add-task',data={'kind':'bad'}).status_code==422
