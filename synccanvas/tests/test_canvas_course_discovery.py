
"""Safe course discovery and backward-compatible class visibility."""

import pytest

from synccanvas import database
from synccanvas.services.canvas_course_discovery import (
    discover_courses,
    discover_from_http,
)
from synccanvas.services.canvas_reader import CanvasReadError


def test_discovers_courses_without_creating_classes():
    courses = discover_courses(lambda: [
        {"id": 7, "name": "Math", "course_code": "M7"},
        {"id": 8, "name": "Student Resources"},
    ])

    assert [x.canvas_course_id for x in courses] == [7, 8]
    assert courses[0].course_code == "M7"


def test_duplicate_courses_only_once():
    assert len(discover_courses(lambda: [
        {"id": 7, "name": "Math"},
        {"id": 7, "name": "Math"},
    ])) == 1


def test_skips_unnamed_and_invalid_ids():
    assert discover_courses(lambda: [
        {"id": True, "name": "Bad"},
        {"id": 0, "name": "Bad"},
        {"id": 2, "name": " "},
    ]) == []


def test_invalid_response_rejected():
    with pytest.raises(CanvasReadError):
        discover_courses(lambda: {"id": 7})


def test_invalid_entry_rejected():
    with pytest.raises(CanvasReadError):
        discover_courses(lambda: [None])


def test_http_uses_existing_client_interface():
    class FakeClient:
        def get_list(self, path):
            assert path == "/api/v1/courses?per_page=100"
            return [{"id": 7, "name": "Math"}]

    assert discover_from_http(FakeClient())[0].name == "Math"


def test_existing_classes_remain_enabled(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        database,
        "DB_PATH",
        tmp_path / "upgrade.sqlite3",
    )

    with database.db() as conn:
        conn.execute(
            "INSERT INTO classes(name) VALUES ('Math')"
        )

    with database.db() as conn:
        row = conn.execute(
            "SELECT enabled, archived FROM classes"
        ).fetchone()

        assert (
            row["enabled"],
            row["archived"],
        ) == (1, 0)


def test_flags_can_be_changed_without_deleting_class(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        database,
        "DB_PATH",
        tmp_path / "flags.sqlite3",
    )

    with database.db() as conn:
        conn.execute(
            "INSERT INTO classes(name) VALUES ('Math')"
        )
        conn.execute("""
            UPDATE classes
            SET enabled=0, archived=1
            WHERE name='Math'
        """)

    with database.db() as conn:
        row = conn.execute("""
            SELECT name, enabled, archived
            FROM classes
        """).fetchone()

        assert (
            row["name"],
            row["enabled"],
            row["archived"],
        ) == ("Math", 0, 1)
