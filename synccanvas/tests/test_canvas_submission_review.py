"""Canvas submission is sufficient for completion, with optional parent review."""
from fastapi.testclient import TestClient
from synccanvas import database
from synccanvas.main import app
from synccanvas.services.canvas_import_worker import CanvasImportWorker
from synccanvas.services.canvas_storage import link_canvas_course


def test_submission_marks_done_and_parent_can_review(tmp_path, monkeypatch):
    monkeypatch.setattr(database, 'DB_PATH', tmp_path / 'submitted.sqlite3')
    with database.db() as conn:
        conn.execute("INSERT INTO classes(id,name) VALUES(1,'Math')")
        link_canvas_course(conn, 7, 1)
    state = {'submitted': False}
    def fetch(_):
        return [{'id': 42, 'name': 'Fractions', 'due_at': '2020-01-01T12:00:00Z',
                 'html_url': 'https://school.instructure.com/courses/7/assignments/42',
                 'submission': {'workflow_state': 'submitted' if state['submitted'] else 'unsubmitted'}}]
    worker = CanvasImportWorker(fetch)
    worker.run()
    with database.db() as conn:
        assert conn.execute('SELECT completed FROM canvas_assignments').fetchone()[0] == 0
    state['submitted'] = True
    worker.run()
    client = TestClient(app)
    parent = client.get('/parent').text
    assert 'Canvas submissions to review' in parent
    assert 'Needs review' in parent
    assert 'https://school.instructure.com/courses/7/assignments/42' in parent
    assert 'Past due — check together' not in parent or 'Fractions (due' not in parent
    with database.db() as conn:
        row = conn.execute('SELECT id, completed, canvas_submitted FROM canvas_assignments').fetchone()
        assert (row['completed'], row['canvas_submitted']) == (1,1)
        assignment_id = row['id']
    response = client.post(f'/parent/canvas/{assignment_id}/review', follow_redirects=False)
    assert response.status_code == 303
    assert 'Needs review' not in client.get('/parent').text
    worker.run()
    assert 'Needs review' not in client.get('/parent').text


def test_manual_completion_is_not_undone(tmp_path, monkeypatch):
    monkeypatch.setattr(database, 'DB_PATH', tmp_path / 'manual.sqlite3')
    with database.db() as conn:
        conn.execute("INSERT INTO classes(id,name) VALUES(1,'Math')")
        link_canvas_course(conn, 7, 1)
    worker = CanvasImportWorker(lambda _: [{'id': 42, 'name': 'Paper task'}])
    worker.run()
    with database.db() as conn:
        conn.execute('UPDATE canvas_assignments SET completed=1')
    worker.run()
    with database.db() as conn:
        assert conn.execute('SELECT completed FROM canvas_assignments').fetchone()[0] == 1
