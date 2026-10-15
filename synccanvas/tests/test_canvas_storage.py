
"""SQLite integration tests for Canvas assignment imports."""

import sqlite3

import pytest

from synccanvas import database
from synccanvas.services.canvas_mapping import map_assignments
from synccanvas.services.canvas_reconciliation import ReconciliationError
from synccanvas.services.canvas_storage import (
    import_canvas_assignments,
    link_canvas_course,
    load_canvas_assignments,
)


@pytest.fixture
def connection(tmp_path, monkeypatch):
    monkeypatch.setattr(
        database,
        "DB_PATH",
        tmp_path / "synccanvas_test.sqlite3",
    )

    with database.db() as conn:
        conn.execute(
            "INSERT INTO classes (id, name) VALUES (1, 'Math')"
        )
        conn.execute(
            "INSERT INTO classes (id, name) VALUES (2, 'Science')"
        )
        yield conn


def assignments(
    name="Homework",
    assignment_id=123,
    course_id=7,
):
    return map_assignments(
        [{"id": assignment_id, "name": name}],
        course_id,
    )


def test_canvas_tables_created(connection):
    tables = {
        row["name"]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    assert "canvas_course_links" in tables
    assert "canvas_assignments" in tables


def test_existing_tables_preserved(connection):
    tables = {
        row["name"]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    assert {"classes", "entries", "checkins"} <= tables


def test_course_link(connection):
    link_canvas_course(connection, 7, 1)
    row = connection.execute(
        "SELECT class_id FROM canvas_course_links WHERE canvas_course_id=7"
    ).fetchone()
    assert row["class_id"] == 1


def test_cannot_link_missing_class(connection):
    with pytest.raises(ValueError):
        link_canvas_course(connection, 7, 999)


def test_unlinked_course_cannot_import(connection):
    with pytest.raises(ReconciliationError, match="not linked"):
        import_canvas_assignments(connection, 7, assignments())


def test_first_import(connection):
    link_canvas_course(connection, 7, 1)
    result = import_canvas_assignments(connection, 7, assignments())

    assert result.added_count == 1
    assert len(load_canvas_assignments(connection, 7)) == 1


def test_repeated_import_no_duplicates(connection):
    link_canvas_course(connection, 7, 1)

    import_canvas_assignments(connection, 7, assignments())
    result = import_canvas_assignments(connection, 7, assignments())

    assert result.added_count == 0
    assert result.updated_count == 0
    assert result.unchanged_count == 1
    assert len(load_canvas_assignments(connection, 7)) == 1


def test_canvas_title_updates(connection):
    link_canvas_course(connection, 7, 1)

    import_canvas_assignments(connection, 7, assignments())
    result = import_canvas_assignments(
        connection,
        7,
        assignments(name="Revised homework"),
    )

    assert result.updated_count == 1
    assert load_canvas_assignments(connection, 7)[0].title == "Revised homework"


def test_student_fields_preserved(connection):
    link_canvas_course(connection, 7, 1)
    import_canvas_assignments(connection, 7, assignments())

    connection.execute(
        """
        UPDATE canvas_assignments
        SET student_notes='Bring calculator', completed=1
        WHERE canvas_course_id=7 AND canvas_assignment_id=123
        """
    )

    import_canvas_assignments(
        connection,
        7,
        assignments(name="Updated homework"),
    )

    record = load_canvas_assignments(connection, 7)[0]
    assert record.student_notes == "Bring calculator"
    assert record.completed is True


def test_manual_entries_untouched(connection):
    link_canvas_course(connection, 7, 1)

    connection.execute(
        """
        INSERT INTO entries (class_id, kind, details, done)
        VALUES (1, 'Homework', 'My own task', 1)
        """
    )

    import_canvas_assignments(connection, 7, assignments())

    row = connection.execute(
        "SELECT details, done FROM entries"
    ).fetchone()

    assert row["details"] == "My own task"
    assert row["done"] == 1


def test_wrong_course_rejected(connection):
    link_canvas_course(connection, 7, 1)

    with pytest.raises(ReconciliationError, match="different"):
        import_canvas_assignments(
            connection,
            7,
            assignments(course_id=8),
        )


def test_duplicate_import_rolls_back(connection):
    link_canvas_course(connection, 7, 1)
    items = assignments()

    with pytest.raises(ReconciliationError, match="Duplicate"):
        import_canvas_assignments(
            connection,
            7,
            [items[0], items[0]],
        )

    assert load_canvas_assignments(connection, 7) == []


def test_import_keeps_missing_assignments(connection):
    link_canvas_course(connection, 7, 1)
    import_canvas_assignments(connection, 7, assignments())

    import_canvas_assignments(connection, 7, [])

    assert len(load_canvas_assignments(connection, 7)) == 1


def test_two_courses_can_share_assignment_number(connection):
    link_canvas_course(connection, 7, 1)
    link_canvas_course(connection, 8, 2)

    import_canvas_assignments(connection, 7, assignments())
    import_canvas_assignments(
        connection,
        8,
        assignments(course_id=8),
    )

    assert len(load_canvas_assignments(connection, 7)) == 1
    assert len(load_canvas_assignments(connection, 8)) == 1


def test_invalid_link_identifiers(connection):
    with pytest.raises(ValueError):
        link_canvas_course(connection, True, 1)


def test_database_foreign_keys_enabled(connection):
    enabled = connection.execute("PRAGMA foreign_keys").fetchone()[0]
    assert enabled == 1
