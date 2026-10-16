"""Regression tests for the two-state task workflow."""
import pytest
from fastapi.testclient import TestClient
from synccanvas import database, main

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(database, 'DB_PATH', tmp_path / 'tasks.sqlite3')
    with TestClient(main.app) as c:
        yield c

def add_task(client):
    client.post('/classes', data={'name':'Math'})
    client.post('/classes/1/entries', data={'kind':'Homework','details':'Worksheet'})

def test_student_only_marks_done_from_homework_review(client):
    add_task(client)
    student = client.get('/').text
    assert 'Worksheet' in student
    assert '/entries/1/done' not in student
    assert '/entries/1/edit' not in student
    assert '/entries/1/delete' not in student
    home = client.get('/home').text
    assert '/entries/1/done' in home
    assert client.post('/entries/1/done').status_code == 200
    assert 'Worksheet' not in client.get('/home').text
    assert 'Student says done' in client.get('/parent').text
    client.post('/parent/entries/1/confirm')
    assert 'Parent confirmed' in client.get('/parent').text
    client.post('/parent/entries/1/return')
    assert 'Worksheet' in client.get('/home').text

def test_parent_can_edit_and_delete(client):
    add_task(client)
    parent=client.get('/parent').text
    assert '/entries/1/edit' in parent
    assert '/parent/entries/1/delete' in parent
    response=client.post('/entries/1/edit',data={'kind':'Study','details':'Chapter 3'})
    assert response.status_code == 200
    assert 'Chapter 3' in client.get('/parent').text
    assert client.post('/parent/entries/1/delete').status_code == 200
    assert 'Chapter 3' not in client.get('/parent').text
    assert client.post('/parent/entries/1/delete').status_code == 404

def test_imported_canvas_table_is_untouched(client):
    add_task(client)
    with database.db() as conn:
        conn.execute('INSERT INTO canvas_assignments(canvas_course_id,canvas_assignment_id,title) VALUES (101,202,\'Canvas worksheet\')')
    client.post('/parent/entries/1/delete')
    with database.db() as conn:
        assert conn.execute('SELECT COUNT(*) FROM canvas_assignments').fetchone()[0] == 1
