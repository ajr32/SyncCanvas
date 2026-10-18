"""Issue #90: missing and unconfirmed class entries in the family workflow."""
import pytest
from fastapi.testclient import TestClient
from synccanvas import database
from synccanvas.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(database, 'DB_PATH', tmp_path / 'issue90.sqlite3')
    with database.db() as conn:
        conn.execute("INSERT INTO classes(id,name,enabled,archived) VALUES (1,'Math',1,0)")
        conn.execute("INSERT INTO classes(id,name,enabled,archived) VALUES (2,'Science',1,0)")
        conn.execute("INSERT INTO classes(id,name,enabled,archived) VALUES (3,'Disabled',0,0)")
        conn.execute("INSERT INTO classes(id,name,enabled,archived) VALUES (4,'Archived',1,1)")
    return TestClient(app)


def test_missing_entries_are_visible_to_student_and_parent(client):
    student = client.get('/')
    parent = client.get('/parent')
    assert student.status_code == parent.status_code == 200
    assert student.text.count('Not checked yet') == 2
    assert '0/2' in parent.text
    assert '2</strong> attention items' in parent.text
    assert 'Disabled' not in student.text and 'Archived' not in student.text
    assert '<strong>Disabled</strong>' not in parent.text and '<strong>Archived</strong>' not in parent.text


def test_checked_but_unconfirmed_is_not_nothing_tonight(client):
    assert client.post('/classes/1/checkin').status_code == 200
    student = client.get('/').text
    parent = client.get('/parent').text
    assert 'Checked today' in student
    assert 'Nothing tonight' not in parent
    assert '1/2' in parent
    assert '1</strong> attention items' in parent


def test_explicit_nothing_tonight_is_distinct_from_missing(client):
    assert client.post('/classes/1/nothing').status_code == 200
    student = client.get('/').text
    parent = client.get('/parent').text
    assert 'Nothing tonight' in student and 'Nothing tonight' in parent
    assert 'Not checked yet' in student and 'Not checked yet' in parent
    assert '1/2' in parent


def test_new_task_checks_in_class_but_does_not_confirm_no_work(client):
    response = client.post('/classes/1/entries', data={'kind':'Homework','details':'Worksheet'})
    assert response.status_code == 200
    parent = client.get('/parent').text
    assert 'Worksheet' in parent
    assert 'Checked today' in parent
    assert 'Nothing tonight' not in parent
    assert '1/2' in parent


def test_missing_class_cannot_be_checked(client):
    assert client.post('/classes/999/checkin').status_code == 404
    assert client.post('/classes/999/nothing').status_code == 404
    assert '0/2' in client.get('/parent').text
