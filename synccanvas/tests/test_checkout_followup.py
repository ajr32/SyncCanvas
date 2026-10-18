"""Simple end-of-day check-out: review classes and catch missing notes."""
import pytest
from fastapi.testclient import TestClient
from synccanvas import database
from synccanvas.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "checkout.sqlite3")
    with database.db() as conn:
        conn.execute("INSERT INTO classes(name) VALUES ('Math')")
        conn.execute("INSERT INTO classes(name) VALUES ('Science')")
    return TestClient(app)


def test_review_each_class(client):
    page = client.get('/review').text
    assert '0 of 2' in page
    assert 'Math' in page and 'Science' in page
    assert 'No work recorded for this class' in page
    assert 'Who reviewed?' not in page
    assert 'Follow-up status' not in page
    assert 'Ready-to-go checklist' not in page
    assert client.post('/school/classes/1/review', data={'outcome': 'reviewed'}).status_code == 200
    assert '1 of 2' in client.get('/review').text
    client.post('/school/classes/2/review', data={'outcome': 'reviewed'})
    assert 'All classes reviewed.' in client.get('/review').text


def test_missing_information_can_be_noted(client):
    response = client.post('/school/classes/1/question', data={'question': 'Bring math workbook home'})
    assert response.status_code == 200
    assert 'Bring math workbook home' in client.get('/review').text
    assert 'Bring math workbook home' in client.get('/parent').text
    assert 'Add it to your class notes' in client.get('/review').text


def test_note_is_escaped(client):
    client.post('/school/classes/1/question', data={'question': '<script>alert(1)</script>'})
    page = client.get('/review').text
    assert '&lt;script&gt;' in page
    assert '<script>alert(1)</script>' not in page
