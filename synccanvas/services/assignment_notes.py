
"""Family notes attached to individual Canvas assignments."""

from synccanvas.database import db


def _ensure_table(conn):
    """Create the notes table without changing Canvas data."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS assignment_notes (
            canvas_assignment_id INTEGER PRIMARY KEY
                REFERENCES canvas_assignments(id),
            teacher_note TEXT NOT NULL DEFAULT '',
            parent_note TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def get_assignment_notes(assignment_id: int) -> dict:
    """Return the saved notes, or blank notes if none exist."""
    with db() as conn:
        _ensure_table(conn)

        row = conn.execute(
            """
            SELECT teacher_note, parent_note, updated_at
            FROM assignment_notes
            WHERE canvas_assignment_id = ?
            """,
            (assignment_id,),
        ).fetchone()

    if row is None:
        return {
            "teacher_note": "",
            "parent_note": "",
            "updated_at": None,
        }

    return dict(row)


def save_assignment_notes(
    assignment_id: int,
    teacher_note: str,
    parent_note: str,
) -> None:
    """Save family notes without modifying imported Canvas fields."""
    if not isinstance(teacher_note, str):
        raise ValueError("Teacher note must be text.")

    if not isinstance(parent_note, str):
        raise ValueError("Parent note must be text.")

    with db() as conn:
        _ensure_table(conn)

        assignment = conn.execute(
            """
            SELECT id
            FROM canvas_assignments
            WHERE id = ?
            """,
            (assignment_id,),
        ).fetchone()

        if assignment is None:
            raise ValueError("Assignment does not exist.")

        conn.execute(
            """
            INSERT INTO assignment_notes (
                canvas_assignment_id,
                teacher_note,
                parent_note
            )
            VALUES (?, ?, ?)
            ON CONFLICT(canvas_assignment_id)
            DO UPDATE SET
                teacher_note = excluded.teacher_note,
                parent_note = excluded.parent_note,
                updated_at = CURRENT_TIMESTAMP
            """,
            (assignment_id, teacher_note, parent_note),
        )
