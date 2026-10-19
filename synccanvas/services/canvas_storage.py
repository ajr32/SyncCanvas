
"""Safe persistence of Canvas assignments in SyncCanvas SQLite."""

from __future__ import annotations

import sqlite3
import json
from collections.abc import Iterable

from synccanvas.services.canvas_mapping import MappedAssignment
from synccanvas.services.canvas_reconciliation import (
    PlannerAssignment,
    ReconciliationError,
    ReconciliationResult,
    reconcile_assignments,
)


def link_canvas_course(
    conn: sqlite3.Connection,
    canvas_course_id: int,
    class_id: int,
) -> None:
    """Link a Canvas course to an existing planner class."""
    if (
        isinstance(canvas_course_id, bool)
        or not isinstance(canvas_course_id, int)
        or canvas_course_id <= 0
        or isinstance(class_id, bool)
        or not isinstance(class_id, int)
        or class_id <= 0
    ):
        raise ValueError("Invalid course or class identifier.")

    existing = conn.execute(
        "SELECT id FROM classes WHERE id = ?",
        (class_id,),
    ).fetchone()

    if existing is None:
        raise ValueError("Planner class does not exist.")

    conn.execute(
        """
        INSERT INTO canvas_course_links (
            canvas_course_id, class_id
        )
        VALUES (?, ?)
        ON CONFLICT(canvas_course_id)
        DO UPDATE SET class_id = excluded.class_id
        """,
        (canvas_course_id, class_id),
    )


def load_canvas_assignments(
    conn: sqlite3.Connection,
    course_id: int,
) -> list[PlannerAssignment]:
    """Load imported assignments for one Canvas course."""
    rows = conn.execute(
        """
        SELECT *
        FROM canvas_assignments
        WHERE canvas_course_id = ?
        ORDER BY id
        """,
        (course_id,),
    ).fetchall()

    return [
        PlannerAssignment(
            canvas_id=row["canvas_assignment_id"],
            course_id=row["canvas_course_id"],
            title=row["title"],
            description=row["description"],
            due_at=row["due_at"],
            due_date=row["due_date"],
            html_url=row["html_url"],
            student_notes=row["student_notes"],
            completed=bool(row["completed"]),
            submission_types=tuple(json.loads(row["submission_types"])) if "submission_types" in row.keys() else (),
            canvas_submitted=bool(row["canvas_submitted"]) if "canvas_submitted" in row.keys() else False,
            canvas_missing=bool(row["canvas_missing"]) if "canvas_missing" in row.keys() else False,
            review_dismissed=bool(row["review_dismissed"]) if "review_dismissed" in row.keys() else False,
        )
        for row in rows
    ]


def import_canvas_assignments(
    conn: sqlite3.Connection,
    course_id: int,
    assignments: Iterable[MappedAssignment],
) -> ReconciliationResult:
    """Atomically import a linked course's Canvas assignments.

    Existing student notes and completion flags are preserved.
    Student-entered entries are never modified.
    """
    items = tuple(assignments)

    for item in items:
        if not isinstance(item, MappedAssignment):
            raise ReconciliationError("Invalid imported assignment.")
        if item.course_id != course_id:
            raise ReconciliationError(
                "Assignment belongs to a different Canvas course."
            )

    try:
        conn.execute("SAVEPOINT canvas_import")

        linked = conn.execute(
            """
            SELECT class_id
            FROM canvas_course_links
            WHERE canvas_course_id = ?
            """,
            (course_id,),
        ).fetchone()

        if linked is None:
            raise ReconciliationError(
                "Canvas course is not linked to a planner class."
            )

        existing = load_canvas_assignments(conn, course_id)
        result = reconcile_assignments(existing, items)

        for record in (*result.added, *result.updated):
            conn.execute(
                """
                INSERT INTO canvas_assignments (
                    canvas_course_id,
                    canvas_assignment_id,
                    title,
                    description,
                    due_at,
                    due_date,
                    html_url,
                    submission_types, canvas_submitted, canvas_missing, completed, last_seen_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(
                    canvas_course_id,
                    canvas_assignment_id
                )
                DO UPDATE SET
                    title = excluded.title,
                    description = excluded.description,
                    due_at = excluded.due_at,
                    due_date = excluded.due_date,
                    html_url = excluded.html_url,
                    submission_types = excluded.submission_types,
                    canvas_submitted = excluded.canvas_submitted,
                    canvas_missing = excluded.canvas_missing,
                    completed = CASE WHEN canvas_assignments.completed=1 OR excluded.canvas_submitted=1 THEN 1 ELSE 0 END,
                    missing_from_canvas = 0,
                    last_seen_at = CURRENT_TIMESTAMP
                """,
                (
                    record.course_id,
                    record.canvas_id,
                    record.title,
                    record.description,
                    record.due_at,
                    record.due_date,
                    record.html_url,
                    json.dumps(record.submission_types),
                    int(record.canvas_submitted),
                    int(record.canvas_missing),
                    int(record.completed),
                ),
            )

        # A successful full-course fetch is the only evidence for absence.
        # Never delete an imported assignment or a family task linked to it.
        seen_ids = [item.canvas_id for item in items]
        if seen_ids:
            placeholders = ",".join("?" for _ in seen_ids)
            conn.execute(f"""UPDATE canvas_assignments
                SET missing_from_canvas=1
                WHERE canvas_course_id=? AND canvas_assignment_id NOT IN ({placeholders})""",
                (course_id, *seen_ids))
        else:
            conn.execute("UPDATE canvas_assignments SET missing_from_canvas=1 WHERE canvas_course_id=?", (course_id,))
        conn.execute("""UPDATE canvas_assignments
            SET missing_from_canvas=0, last_seen_at=CURRENT_TIMESTAMP
            WHERE canvas_course_id=? AND missing_from_canvas=0""", (course_id,))
        conn.execute("RELEASE SAVEPOINT canvas_import")
        return result

    except Exception:
        conn.execute("ROLLBACK TO SAVEPOINT canvas_import")
        conn.execute("RELEASE SAVEPOINT canvas_import")
        raise
