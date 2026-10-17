from datetime import date
from fastapi.testclient import TestClient
from synccanvas.main import app
from synccanvas.database import db
from synccanvas.services.recurring import ensure_today


def test_recurring_expectations_generate_once_and_pause(tmp_path, monkeypatch):
    import synccanvas.database as storage
    monkeypatch.setattr(storage, 'DB_PATH', tmp_path / 'recurring.sqlite3')
    client=TestClient(app)
    client.post('/classes', data={'name':'Mathematics 7'})
    with db() as conn:
        cid=conn.execute("SELECT id FROM classes WHERE name='Mathematics 7'").fetchone()['id']
    response=client.post('/settings/expectations/add', data={'class_id':cid,'kind':'Study',
        'details':'Practice math for 20 minutes','frequency':'daily'}, follow_redirects=False)
    assert response.status_code==303
    assert 'Practice math for 20 minutes' in client.get('/settings').text
    assert 'Practice math for 20 minutes' in client.get('/afternoon').text
    client.get('/afternoon')
    with db() as conn:
        count=conn.execute("SELECT count(*) FROM entries WHERE details='Practice math for 20 minutes'").fetchone()[0]
        rid=conn.execute('SELECT id FROM recurring_expectations').fetchone()['id']
    assert count==1
    client.post(f'/settings/expectations/{rid}/toggle')
    with db() as conn:
        ensure_today(conn, '2026-10-20')
        count=conn.execute('SELECT count(*) FROM recurring_instances').fetchone()[0]
    assert count==1


def test_weekday_rule_skips_weekend(tmp_path, monkeypatch):
    import synccanvas.database as storage
    monkeypatch.setattr(storage, 'DB_PATH', tmp_path / 'weekdays.sqlite3')
    client=TestClient(app)
    client.post('/classes', data={'name':'Mathematics 7'})
    with db() as conn:
        cid=conn.execute('SELECT id FROM classes').fetchone()['id']
    client.post('/settings/expectations/add', data={'class_id':cid,'kind':'Study',
        'details':'Weekday math','frequency':'weekdays'})
    with db() as conn:
        ensure_today(conn, '2026-10-17')  # Saturday
        assert conn.execute('SELECT count(*) FROM recurring_instances').fetchone()[0]==0
        ensure_today(conn, '2026-10-19')  # Monday
        ensure_today(conn, '2026-10-19')
        assert conn.execute('SELECT count(*) FROM recurring_instances').fetchone()[0]==1


def test_invalid_frequency_is_rejected(tmp_path, monkeypatch):
    import synccanvas.database as storage
    monkeypatch.setattr(storage, 'DB_PATH', tmp_path / 'invalid.sqlite3')
    client=TestClient(app)
    response=client.post('/settings/expectations/add',data={'class_id':1,'kind':'Study',
        'details':'Practice','frequency':'hourly'})
    assert response.status_code==422
