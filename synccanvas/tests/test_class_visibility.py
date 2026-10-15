
"""Regression tests for student visibility and Canvas import eligibility."""

import pytest
from fastapi.testclient import TestClient

from synccanvas import database
from synccanvas.main import app
from synccanvas.services.canvas_import_worker import CanvasImportWorker


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr(
        database,
        "DB_PATH",
        tmp_path / "visibility.sqlite3",
    )

    with database.db() as conn:
        conn.execute(
            """
            INSERT INTO classes(id, name, enabled, archived)
            VALUES
                (1, 'Mathematics 7', 1, 0),
                (2, 'Student Resources', 0, 0),
                (3, 'Physical Education Q1', 1, 1)
            """
        )
        conn.execute(
            """
            INSERT INTO canvas_course_links(
                canvas_course_id, class_id
            )
            VALUES (101, 1), (102, 2), (103, 3)
            """
        )


def test_student_sees_only_active_classes(isolated_db):
    response = TestClient(app).get("/")

    assert response.status_code == 200
    assert "Mathematics 7" in response.text
    assert "Student Resources" not in response.text
    assert "Physical Education Q1" not in response.text
    assert '<h3>Add a class</h3>' not in response.text


def test_review_hides_disabled_and_archived(isolated_db):
    response = TestClient(app).get("/review")

    assert response.status_code == 200
    assert "Mathematics 7" in response.text
    assert "Student Resources" not in response.text
    assert "Physical Education Q1" not in response.text


def test_parent_has_manage_classes_link(isolated_db):
    response = TestClient(app).get("/parent")

    assert response.status_code == 200
    assert 'href="/parent/classes"' in response.text


def test_canvas_worker_skips_disabled_and_archived(isolated_db):
    fetched = []

    def fetch(course_id):
        fetched.append(course_id)
        return []

    summary = CanvasImportWorker(fetch).run()

    assert fetched == [101]
    assert summary.courses_processed == 1


def test_restoring_class_reenables_import(isolated_db):
    with database.db() as conn:
        conn.execute(
            """
            UPDATE classes
            SET enabled=1, archived=0
            WHERE id IN (2, 3)
            """
        )

    fetched = []

    def fetch(course_id):
        fetched.append(course_id)
        return []

    summary = CanvasImportWorker(fetch).run()

    assert fetched == [101, 102, 103]
    assert summary.courses_processed == 3
