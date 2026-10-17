"""Date-specific closures and shortened school day behavior."""
from datetime import date as RealDate
from fastapi.testclient import TestClient
from synccanvas import database, pages
from synccanvas.main import app

class Monday:
    @staticmethod
    def today(): return RealDate(2026,10,19)

def setup(tmp_path,monkeypatch):
    monkeypatch.setattr(database,'DB_PATH',tmp_path/'days.sqlite3')
    monkeypatch.setattr(pages,'family_today',Monday.today)
    with database.db() as conn:
        conn.execute("INSERT INTO classes(id,name) VALUES(1,'Math')")
        conn.execute("INSERT INTO bell_periods(id,label,start_time,end_time,weekdays) VALUES(1,'1','08:00','08:50','01234')")
        conn.execute('INSERT INTO class_periods(class_id,period_id) VALUES(1,1)')
    return TestClient(app)

def test_closed_day_hides_period_and_restores(tmp_path,monkeypatch):
    client=setup(tmp_path,monkeypatch)
    assert 'Period 1' in client.get('/').text
    response=client.post('/parent/school-days/save',data={'day':'2026-10-19','kind':'closed','note':'Holiday'},follow_redirects=False)
    assert response.status_code==303
    page=client.get('/').text
    assert 'No school today' in page and 'Holiday' in page
    assert 'Period 1' not in page
    assert client.post('/parent/school-days/2026-10-19/delete',follow_redirects=False).status_code==303
    assert 'Period 1' in client.get('/').text

def test_shortened_day_time_override_and_validation(tmp_path,monkeypatch):
    client=setup(tmp_path,monkeypatch)
    assert client.post('/parent/school-days/save',data={'day':'2026-10-19','kind':'shortened','note':'Early dismissal'}).status_code==200
    assert client.post('/parent/school-days/2026-10-19/period/1',data={'start_time':'9:15 AM','end_time':'9:45 AM'},follow_redirects=False).status_code==303
    assert '9:15 AM' in client.get('/').text
    with database.db() as conn:
        row=conn.execute('SELECT * FROM school_day_periods').fetchone()
        assert row['start_time']=='09:15'
    assert client.post('/parent/school-days/2026-10-19/period/1',data={'start_time':'10:00 AM','end_time':'9:00 AM'}).status_code==400
    assert client.post('/parent/school-days/2026-10-19/period/1',data={'start_time':'','end_time':''},follow_redirects=False).status_code==303
    with database.db() as conn: assert conn.execute('SELECT count(*) FROM school_day_periods').fetchone()[0]==0

def test_invalid_date_and_closed_day_cannot_set_times(tmp_path,monkeypatch):
    client=setup(tmp_path,monkeypatch)
    assert client.post('/parent/school-days/save',data={'day':'2026-02-30','kind':'closed'}).status_code==400
    assert client.post('/parent/school-days/save',data={'day':'2026-10-19','kind':'closed'}).status_code==200
    assert client.post('/parent/school-days/2026-10-19/period/1',data={'start_time':'09:00','end_time':'10:00'}).status_code==400
