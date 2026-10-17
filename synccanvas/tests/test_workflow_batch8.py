"""Durable school review, physical paper checks and question follow-up."""
import pytest
from fastapi.testclient import TestClient
from synccanvas.main import app
from synccanvas.database import db
from synccanvas.pages import today

@pytest.fixture
def client(tmp_path, monkeypatch):
    import synccanvas.database as storage
    monkeypatch.setattr(storage,'DB_PATH',tmp_path/'batch8.sqlite3')
    with db() as conn:
        conn.execute("INSERT INTO classes(id,name) VALUES (1,'Math'),(2,'English')")
    return TestClient(app)

def test_class_review_is_separate_from_student_checkin(client):
    assert client.post('/school/classes/1/review',data={'outcome':'nothing'}).status_code==200
    with db() as conn:
        assert conn.execute('SELECT outcome FROM school_reviews WHERE class_id=1').fetchone()[0]=='nothing'
        assert conn.execute('SELECT count(*) FROM checkins').fetchone()[0]==0
    assert '1 of 2' in client.get('/review').text
    assert client.post('/school/classes/1/review',data={'outcome':'reviewed'}).status_code==200
    with db() as conn:
        assert conn.execute('SELECT count(*) FROM school_reviews').fetchone()[0]==1

def test_papers_save_and_can_be_corrected(client):
    client.post('/school/papers',data={'pocket_checked':'yes','notes':'One loose page'})
    assert 'One loose page' in client.get('/review').text
    assert 'Pocket checked: yes' in client.get('/parent').text
    client.post('/school/papers',data={'backpack_checked':'yes'})
    with db() as conn:
        row=conn.execute('SELECT pocket_checked,backpack_checked,notes FROM paper_reviews WHERE day=?',(today(),)).fetchone()
        assert tuple(row)==(0,1,'')

def test_question_parent_visibility_and_resolution(client):
    client.post('/school/classes/2/question',data={'question':'Ask about missing handout'})
    assert 'Ask about missing handout' in client.get('/parent').text
    client.post('/school/classes/2/question',data={'question':'Ask about missing handout','resolved':'yes'})
    assert 'No unresolved questions recorded today' in client.get('/parent').text

def test_bad_inputs_and_missing_class(client):
    assert client.post('/school/classes/1/review',data={'outcome':'unverified'}).status_code==422
    assert client.post('/school/classes/999/review',data={'outcome':'reviewed'}).status_code==404
    assert client.post('/school/classes/999/question',data={'question':'missing'}).status_code==404
    assert client.post('/school/papers',data={'notes':'x'*301}).status_code==422

def test_question_is_escaped(client):
    client.post('/school/classes/1/question',data={'question':'<script>alert(1)</script>'})
    response=client.get('/parent').text
    assert '&lt;script&gt;' in response
    assert '<script>alert(1)</script>' not in response
