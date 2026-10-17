
"""Parent review operations for SyncCanvas.

This module owns parent confirmation, returning work for
another look, and coaching notes. It does not own HTTP routes.
"""

from synccanvas.database import db


class ParentReviewError(Exception):
    """A parent review action could not be completed."""

    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


def confirm_task(entry_id: int) -> None:
    """Confirm a task that the student marked complete."""
    with db() as conn:
        result = conn.execute(
            """
            UPDATE entries
            SET parent_confirmed = 1
            WHERE id = ?
              AND done = 1
              AND kind != 'Nothing Tonight'
            """,
            (entry_id,),
        )

        if result.rowcount == 0:
            raise ParentReviewError(
                409,
                "Only completed tasks can be confirmed",
            )


def return_task(entry_id: int) -> None:
    """Return completed work to the student's open tasks."""
    with db() as conn:
        result = conn.execute(
            """
            UPDATE entries
            SET done = 0,
                progress = 'not_started',
                completed_at = NULL,
                parent_confirmed = 0
            WHERE id = ?
              AND done = 1
              AND kind != 'Nothing Tonight'
            """,
            (entry_id,),
        )

        if result.rowcount == 0:
            raise ParentReviewError(
                409,
                "Task must be marked done before returning it",
            )


def save_coaching_note(entry_id: int, note: str) -> None:
    """Save or clear a parent's coaching note."""
    note = note.strip()

    if len(note) > 300:
        raise ParentReviewError(
            422,
            "Coaching note must be 300 characters or fewer",
        )

    with db() as conn:
        result = conn.execute(
            """
            UPDATE entries
            SET coaching_note = ?
            WHERE id = ?
              AND kind != 'Nothing Tonight'
            """,
            (note, entry_id),
        )

        if result.rowcount == 0:
            raise ParentReviewError(
                404,
                "Task not found",
            )
