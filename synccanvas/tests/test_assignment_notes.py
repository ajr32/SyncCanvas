
"""Tests for assignment-specific family notes."""

import pytest

from synccanvas.database import db
from synccanvas.services.assignment_notes import (
    get_assignment_notes,
    save_assignment_notes,
)


@pytest.fixture
def assignment_id(tmp_path, monkeypatch):
    import synccanvas.database as storage

    monkeypatch.setattr(
        storage,
        "DB_PATH",
        tmp_path / "assignment_notes.sqlite3",
    )

    with db() as conn:
        conn.execute(
            """
            INSERT INTO canvas_assignments (
                id, canvas_course_id, canvas_assignment_id,
                title
            )
            VALUES (1, 100, 200, 'Geography Quiz')
            """
        )

    return 1


def test_new_assignment_has_blank_notes(assignment_id):
    notes = get_assignment_notes(assignment_id)

    assert notes["teacher_note"] == ""
    assert notes["parent_note"] == ""


def test_save_and_retrieve_notes(assignment_id):
    save_assignment_notes(
        assignment_id,
        "Study vocabulary for Friday.",
        "Practice three difficult definitions.",
    )

    notes = get_assignment_notes(assignment_id)

    assert notes["teacher_note"] == "Study vocabulary for Friday."
    assert notes["parent_note"] == "Practice three difficult definitions."


def test_edit_notes(assignment_id):
    save_assignment_notes(assignment_id, "Original", "Parent")
    save_assignment_notes(assignment_id, "Updated", "New parent note")

    notes = get_assignment_notes(assignment_id)

    assert notes["teacher_note"] == "Updated"
    assert notes["parent_note"] == "New parent note"


def test_notes_do_not_change_canvas_assignment(assignment_id):
    save_assignment_notes(
        assignment_id,
        "Review the chapter.",
        "Use flashcards.",
    )

    with db() as conn:
        row = conn.execute(
            "SELECT title FROM canvas_assignments WHERE id = ?",
            (assignment_id,),
        ).fetchone()

    assert row["title"] == "Geography Quiz"


def test_nonexistent_assignment_rejected(assignment_id):
    with pytest.raises(ValueError):
        save_assignment_notes(999, "Teacher", "Parent")
