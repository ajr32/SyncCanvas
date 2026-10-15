
"""End-to-end tests for the opt-in Canvas import worker."""

import pytest

from synccanvas import database
from synccanvas.services.background_sync import BackgroundSync
from synccanvas.services.canvas_import_worker import CanvasImportWorker
from synccanvas.services.canvas_storage import (
    link_canvas_course,
    load_canvas_assignments,
)


@pytest.fixture
def setup_database(tmp_path, monkeypatch):
    monkeypatch.setattr(
        database,
        "DB_PATH",
        tmp_path / "worker_test.sqlite3",
    )

    with database.db() as conn:
        conn.execute(
            "INSERT INTO classes (id, name) VALUES (1, 'Math')"
        )
        conn.execute(
            "INSERT INTO classes (id, name) VALUES (2, 'Science')"
        )
        link_canvas_course(conn, 7, 1)
        link_canvas_course(conn, 8, 2)


def assignment(assignment_id, name):
    return {"id": assignment_id, "name": name}


def test_imports_two_linked_courses(setup_database):
    worker = CanvasImportWorker(
        lambda course_id: [
            assignment(course_id * 10, "Homework")
        ]
    )

    summary = worker.run()

    assert summary.courses_processed == 2
    assert summary.added == 2


def test_repeated_import_is_idempotent(setup_database):
    worker = CanvasImportWorker(
        lambda course_id: [assignment(123, "Homework")]
    )

    first = worker.run()
    second = worker.run()

    assert first.added == 2
    assert second.added == 0
    assert second.unchanged == 2


def test_canvas_title_changes(setup_database):
    title = {"value": "Original"}
    worker = CanvasImportWorker(
        lambda course_id: [assignment(123, title["value"])]
    )

    worker.run()
    title["value"] = "Revised"
    result = worker.run()

    assert result.updated == 2


def test_preserves_student_notes(setup_database):
    worker = CanvasImportWorker(
        lambda course_id: [assignment(123, "Homework")]
    )
    worker.run()

    with database.db() as conn:
        conn.execute(
            """
            UPDATE canvas_assignments
            SET student_notes='My note', completed=1
            WHERE canvas_course_id=7
            """
        )

    worker.run()

    with database.db() as conn:
        record = load_canvas_assignments(conn, 7)[0]

    assert record.student_notes == "My note"
    assert record.completed is True


def test_no_links_means_no_import(tmp_path, monkeypatch):
    monkeypatch.setattr(
        database,
        "DB_PATH",
        tmp_path / "empty.sqlite3",
    )

    with database.db():
        pass

    called = []
    worker = CanvasImportWorker(
        lambda course_id: called.append(course_id)
    )

    summary = worker.run()

    assert summary.courses_processed == 0
    assert called == []


def test_fetch_failure_does_not_partially_import(setup_database):
    def fetch(course_id):
        if course_id == 8:
            raise RuntimeError("Canvas unavailable")
        return [assignment(123, "Homework")]

    worker = CanvasImportWorker(fetch)

    with pytest.raises(RuntimeError):
        worker.run()

    with database.db() as conn:
        assert load_canvas_assignments(conn, 7) == []


def test_invalid_assignment_does_not_partially_import(setup_database):
    def fetch(course_id):
        if course_id == 8:
            return [{"id": 123, "name": ""}]
        return [assignment(123, "Homework")]

    worker = CanvasImportWorker(fetch)

    with pytest.raises(Exception):
        worker.run()

    with database.db() as conn:
        assert load_canvas_assignments(conn, 7) == []


def test_background_sync_success(setup_database):
    worker = CanvasImportWorker(
        lambda course_id: [assignment(123, "Homework")]
    )
    background = BackgroundSync(worker=worker)

    background.request_sync()
    result = background.wait(timeout=5)

    assert result.state.value == "success"
    assert worker.last_summary.added == 2


def test_background_sync_failure_is_safe(setup_database):
    def failing_fetch(course_id):
        raise RuntimeError("SECRET_TOKEN_123")

    background = BackgroundSync(
        worker=CanvasImportWorker(failing_fetch)
    )

    background.request_sync()
    result = background.wait(timeout=5)

    assert result.state.value == "error"
    assert "SECRET_TOKEN_123" not in result.message


def test_worker_requires_fetcher():
    with pytest.raises(ValueError):
        CanvasImportWorker(None)
