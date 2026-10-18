"""Class checkout regression tests for GitHub #74-#78."""
import pytest
from fastapi.testclient import TestClient
from synccanvas import database
from synccanvas.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "checkout.sqlite3")
    with database.db() as conn:
        conn.execute("INSERT INTO classes(id,name) VALUES (1,'Math')")
    return TestClient(app)


def test_checkout_choices_and_due_date(client):
    page = client.get('/review').text
    assert 'Needs clarification' in page
    assert 'Nothing to do' in page
    assert 'Unchecked' in page
    assert 'What must go home?' in page
    assert client.post('/classes/1/entries', data={
        'kind':'Finish Classwork', 'details':'Finish worksheet', 'due_date':'2026-10-22'
    }).status_code == 200
    assert 'Finish worksheet' in client.get('/review').text
    assert 'October 22, 2026' in client.get('/review').text


def test_correction_history_only_on_real_changes(client):
    for outcome in ('needs_followup', 'reviewed', 'reviewed', 'nothing'):
        assert client.post('/school/classes/1/review', data={'outcome':outcome}).status_code == 200
    with database.db() as conn:
        rows = conn.execute('SELECT previous_outcome,new_outcome,corrected_at FROM checkout_corrections ORDER BY id').fetchall()
        assert [(r['previous_outcome'],r['new_outcome']) for r in rows] == [
            ('needs_followup','reviewed'), ('reviewed','nothing')]
        assert all(r['corrected_at'] for r in rows)
    page = client.get('/review').text
    assert 'Earlier corrections' in page
    assert 'Checked — nothing to do' in page


def test_packing_and_invalid_outcomes(client):
    assert client.post('/school/packing/add', data={'item_type':'book','description':'Math workbook'}).status_code == 200
    page = client.get('/review').text
    assert 'Math workbook' in page and 'Not packed' in page
    with database.db() as conn:
        item_id = conn.execute('SELECT id FROM checkout_items').fetchone()['id']
    assert client.post(f'/school/packing/{item_id}/ready',data={'ready':'yes'}).status_code == 200
    assert 'Math workbook' in client.get('/review').text
    assert 'Packed' in client.get('/review').text
    assert client.post('/school/classes/1/review', data={'outcome':'bad'}).status_code == 422
    assert client.post('/school/classes/999/review', data={'outcome':'reviewed'}).status_code == 404
    assert client.post('/school/packing/add',data={'item_type':'book','description':''}).status_code == 422


def test_checkout_escapes_packing_content(client):
    client.post('/school/packing/add',data={'item_type':'paper','description':'<script>alert(1)</script>'})
    page = client.get('/review').text
    assert '&lt;script&gt;' in page
    assert '<script>alert(1)</script>' not in page
