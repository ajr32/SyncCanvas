"""Lunch Buddies tasks behave like homework through parent review."""
from datetime import date as RealDate
from fastapi.testclient import TestClient
from synccanvas import database, pages
from synccanvas.main import app


def setup_lunch(conn):
    conn.execute("INSERT INTO bell_periods(id,label,start_time,end_time,weekdays) VALUES(1,'L','11:30','12:00','01234')")
    conn.execute("INSERT INTO lunch_buddies(id,name,period_id,weekdays) VALUES(1,'Chess',1,'0')")


def test_lunch_task_lifecycle(tmp_path, monkeypatch):
    monkeypatch.setattr(database, 'DB_PATH', tmp_path / 'tasks.sqlite3')
    class Monday:
        @staticmethod
        def today():
            return RealDate(2026, 10, 19)
    monkeypatch.setattr(pages, 'family_today', Monday.today)
    with database.db() as conn:
        setup_lunch(conn)
    client = TestClient(app)
    assert 'Add a note or task' in client.get('/').text
    assert client.post('/parent/lunch-buddies/1/tasks', data={'details': 'Bring permission slip'}, follow_redirects=False).status_code == 303
    with database.db() as conn:
        task_id = conn.execute('SELECT id FROM lunch_tasks').fetchone()[0]
    assert 'Bring permission slip' in client.get('/home').text
    assert client.post(f'/parent/lunch-buddies/tasks/{task_id}/done', follow_redirects=False).status_code == 303
    assert 'Student says done' in client.get('/parent').text
    assert client.post(f'/parent/lunch-buddies/tasks/{task_id}/note', data={'note': 'Good work'}, follow_redirects=False).status_code == 303
    assert client.post(f'/parent/lunch-buddies/tasks/{task_id}/confirm', follow_redirects=False).status_code == 303
    with database.db() as conn:
        row = conn.execute('SELECT * FROM lunch_tasks WHERE id=?', (task_id,)).fetchone()
        assert row['done'] == 1 and row['parent_confirmed'] == 1 and row['coaching_note'] == 'Good work'


def test_lunch_task_validation_and_return(tmp_path, monkeypatch):
    monkeypatch.setattr(database, 'DB_PATH', tmp_path / 'validation.sqlite3')
    with database.db() as conn:
        setup_lunch(conn)
    client = TestClient(app)
    assert client.post('/parent/lunch-buddies/1/tasks', data={'details': '   '}).status_code == 422
    assert client.post('/parent/lunch-buddies/999/tasks', data={'details': 'Test'}).status_code == 404
    client.post('/parent/lunch-buddies/1/tasks', data={'details': 'Bring supplies'})
    with database.db() as conn:
        task_id = conn.execute('SELECT id FROM lunch_tasks').fetchone()[0]
    assert client.post(f'/parent/lunch-buddies/tasks/{task_id}/confirm').status_code == 409
    client.post(f'/parent/lunch-buddies/tasks/{task_id}/done')
    assert client.post(f'/parent/lunch-buddies/tasks/{task_id}/return', follow_redirects=False).status_code == 303
    with database.db() as conn:
        assert conn.execute('SELECT done FROM lunch_tasks WHERE id=?', (task_id,)).fetchone()[0] == 0
    assert client.post(f'/parent/lunch-buddies/tasks/{task_id}/delete', follow_redirects=False).status_code == 303
