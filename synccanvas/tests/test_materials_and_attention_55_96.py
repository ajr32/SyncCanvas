"""Regression coverage for issues #55 and #96."""
from datetime import timedelta
import pytest
from fastapi.testclient import TestClient
from synccanvas import database
from synccanvas.main import app
from synccanvas.services.family_time import family_today

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(database, 'DB_PATH', tmp_path / 'family.sqlite3')
    with database.db() as conn:
        conn.execute("INSERT INTO classes(id,name) VALUES(1,'Math')")
    return TestClient(app)

def test_materials_reusable_and_packing_is_daily(client, monkeypatch):
    assert client.post('/school/classes/1/materials', data={'description':'Notebook'}).status_code == 200
    assert client.post('/school/classes/1/materials', data={'description':'Notebook'}).status_code == 200
    with database.db() as conn:
        items=conn.execute('SELECT id FROM class_materials').fetchall()
        assert len(items)==1
        mid=items[0]['id']
    assert 'Not packed today' in client.get('/review').text
    assert client.post(f'/school/materials/{mid}/packed', data={'packed':'yes'}).status_code==200
    assert 'Packed today' in client.get('/review').text
    with database.db() as conn:
        assert conn.execute('SELECT COUNT(*) FROM material_packing WHERE packed=1').fetchone()[0]==1
    assert client.post(f'/school/materials/{mid}/delete').status_code==200
    assert 'Notebook' not in client.get('/review').text

def test_materials_validation_and_html_escape(client):
    assert client.post('/school/classes/99/materials',data={'description':'Pencil'}).status_code==404
    assert client.post('/school/classes/1/materials',data={'description':'  '}).status_code==422
    assert client.post('/school/materials/999/packed',data={'packed':'yes'}).status_code==404
    client.post('/school/classes/1/materials',data={'description':'<script>alert(1)</script>'})
    page=client.get('/review').text
    assert '&lt;script&gt;' in page and '<script>alert(1)</script>' not in page

def test_parent_attention_late_stuck_and_completed(client):
    past=(family_today()-timedelta(days=2)).isoformat()
    future=(family_today()+timedelta(days=2)).isoformat()
    with database.db() as conn:
        conn.execute("INSERT INTO entries(class_id,kind,details,due_date,progress) VALUES(1,'Homework','Late worksheet',?,'not_started')",(past,))
        conn.execute("INSERT INTO entries(class_id,kind,details,due_date,progress) VALUES(1,'Homework','Need explanation',?,'stuck')",(future,))
        conn.execute("INSERT INTO entries(class_id,kind,details,due_date,progress,done) VALUES(1,'Homework','Finished late',?,'done',1)",(past,))
    page=client.get('/parent').text
    assert 'Past due — check together' in page and 'Late worksheet' in page
    assert 'Needs help — ask what is blocking progress' in page and 'Need explanation' in page
    assert 'Finished late' not in page.split('Work that may need attention</h3>',1)[1].split('</section>',1)[0]
    assert 'penalties' in page
