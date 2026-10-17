from datetime import date, timedelta
from fastapi.testclient import TestClient
from synccanvas.main import app
from synccanvas.database import db


def test_parent_add_and_postpone(tmp_path, monkeypatch):
    import synccanvas.database as storage
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "batch4.sqlite3")
    client=TestClient(app)
    # Uses the shared temporary database fixture from conftest.py.
    client.post('/classes', data={'name':'Mathematics 7'})
    with db() as conn:
        row=conn.execute("SELECT id FROM classes WHERE name='Mathematics 7'").fetchone()
    cid=row['id']
    future=(date.today()+timedelta(days=2)).isoformat()
    response=client.post('/parent/tasks/add', data={'class_id':cid,'kind':'Study',
        'details':'Practice math for 20 minutes','planned_date':future}, follow_redirects=False)
    assert response.status_code==303
    assert 'Practice math for 20 minutes' in client.get('/parent').text
    afternoon = client.get('/afternoon').text
    assert '<summary>Planned for later (1)</summary>' in afternoon
    assert 'Practice math for 20 minutes' in afternoon.split('<summary>Planned for later (1)</summary>', 1)[1]
    assert 'Practice math for 20 minutes' not in afternoon.split('<summary>Planned for later (1)</summary>', 1)[0]
    assert f'Work on {(date.today()+timedelta(days=2)).strftime("%B %d, %Y").replace(" 0", " " )}' in afternoon
    with db() as conn:
        entry=conn.execute("SELECT id,origin FROM entries WHERE details='Practice math for 20 minutes'").fetchone()
    assert entry['origin']=='parent'
    response=client.post(f'/parent/entries/{entry["id"]}/plan',data={'planned_date':''},follow_redirects=False)
    assert response.status_code==303
    assert 'Practice math for 20 minutes' in client.get('/afternoon').text
