"""Lunch Buddies Stage 2 regression checks."""
from datetime import date as RealDate
from fastapi.testclient import TestClient
from synccanvas import database, pages
from synccanvas.main import app

def test_lunch_buddies_create_update_delete(tmp_path, monkeypatch):
    monkeypatch.setattr(database, 'DB_PATH', tmp_path / 'lunch.sqlite3')
    with database.db() as conn:
        conn.execute("INSERT INTO bell_periods(label,start_time,end_time,weekdays) VALUES('L','11:30','12:00','01234')")
    client = TestClient(app)
    assert client.get('/parent/lunch-buddies').status_code == 200
    response = client.post('/parent/lunch-buddies/add', data={'name':'Lunch Buddies','period_id':'1','days':['0','2']}, follow_redirects=False)
    assert response.status_code == 303
    with database.db() as conn:
        row = conn.execute('SELECT * FROM lunch_buddies').fetchone()
        assert row['weekdays'] == '02'
        activity_id = row['id']
    response = client.post(f'/parent/lunch-buddies/{activity_id}/update', data={'name':'Chess Lunch','period_id':'1','days':['1']}, follow_redirects=False)
    assert response.status_code == 303
    with database.db() as conn:
        assert conn.execute('SELECT name FROM lunch_buddies').fetchone()[0] == 'Chess Lunch'
    assert client.post('/parent/lunch-buddies/add', data={'name':'Invalid','period_id':'1','days':['6']}).status_code == 400
    assert client.post(f'/parent/lunch-buddies/{activity_id}/delete', follow_redirects=False).status_code == 303
    with database.db() as conn:
        assert conn.execute('SELECT count(*) FROM lunch_buddies').fetchone()[0] == 0

def test_lunch_buddies_appear_on_matching_day(tmp_path, monkeypatch):
    monkeypatch.setattr(database, 'DB_PATH', tmp_path / 'day.sqlite3')
    monkeypatch.setattr(pages, 'family_today', lambda: RealDate(2026, 10, 19))
    with database.db() as conn:
        conn.execute("INSERT INTO bell_periods(id,label,start_time,end_time,weekdays) VALUES(1,'L','11:30','12:00','01234')")
        conn.execute("INSERT INTO lunch_buddies(name,period_id,weekdays) VALUES('Chess Lunch',1,'0')")
    response = TestClient(app).get('/')
    assert response.status_code == 200
    assert 'Chess Lunch' in response.text
    assert '11:30 AM' in response.text
