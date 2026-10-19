
"""Read-only Canvas assignment adapter for SyncCanvas.

No network calls or credentials are used unless a caller explicitly
supplies a fetch function. This module never writes to Canvas,
SyncCanvas's database, or legacy CanvasSync.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping


class CanvasReadError(Exception):
    """A safe, user-facing Canvas retrieval error."""


@dataclass(frozen=True)
class CanvasAssignment:
    canvas_id: int
    course_id: int
    title: str
    description: str
    due_at: str | None
    html_url: str | None
    submission_types: tuple[str, ...] = ()
    canvas_submitted: bool = False
    canvas_missing: bool = False


def _positive_id(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise CanvasReadError(f"Invalid Canvas {field}.")
    return value


def parse_assignment(
    raw: Mapping[str, Any],
    course_id: int,
) -> CanvasAssignment:
    """Validate one assignment without changing the source data."""
    if not isinstance(raw, Mapping):
        raise CanvasReadError("Invalid Canvas assignment data.")

    course_id = _positive_id(course_id, "course ID")
    assignment_id = _positive_id(raw.get("id"), "assignment ID")

    name = raw.get("name")
    if not isinstance(name, str) or not name.strip():
        raise CanvasReadError("Canvas assignment has no title.")

    description = raw.get("description")
    if description is None:
        description = ""
    if not isinstance(description, str):
        raise CanvasReadError("Invalid Canvas description.")

    due_at = raw.get("due_at")
    if due_at is not None and not isinstance(due_at, str):
        raise CanvasReadError("Invalid Canvas due date.")

    html_url = raw.get("html_url")
    if html_url is not None and not isinstance(html_url, str):
        raise CanvasReadError("Invalid Canvas assignment URL.")

    types = raw.get("submission_types")
    if types is None:
        types = []
    if not isinstance(types, list) or any(
        not isinstance(value, str) or not value.strip() for value in types
    ):
        raise CanvasReadError("Invalid Canvas submission methods.")

    submission = raw.get("submission")
    if submission is not None and not isinstance(submission, Mapping):
        raise CanvasReadError("Invalid Canvas submission information.")
    # Only an actual submission, not a grade or due date, counts as done.
    submitted = bool(submission and (
        submission.get("submitted_at") or
        submission.get("workflow_state") in ("submitted", "graded")
    ))

    return CanvasAssignment(
        canvas_id=assignment_id,
        course_id=course_id,
        title=name.strip(),
        description=description,
        due_at=due_at,
        html_url=html_url,
        submission_types=tuple(types),
        canvas_submitted=submitted,
        canvas_missing=bool(submission and submission.get('missing') is True and not submitted),
    )


class CanvasReader:
    """Retrieve and validate assignments through a read-only callback."""

    def __init__(
        self,
        fetch_assignments: Callable[[int], list[dict[str, Any]]] | None = None,
    ) -> None:
        self._fetch_assignments = fetch_assignments

    @property
    def configured(self) -> bool:
        return self._fetch_assignments is not None

    def assignments_for_course(self, course_id: int) -> list[CanvasAssignment]:
        course_id = _positive_id(course_id, "course ID")

        if self._fetch_assignments is None:
            raise CanvasReadError("Canvas is not connected yet.")

        try:
            response = self._fetch_assignments(course_id)
        except Exception as exc:
            raise CanvasReadError(
                "Couldn't retrieve Canvas assignments. Try again later."
            ) from exc

        if not isinstance(response, list):
            raise CanvasReadError("Invalid Canvas assignment response.")

        assignments = [
            parse_assignment(item, course_id)
            for item in response
        ]

        ids = [item.canvas_id for item in assignments]
        if len(ids) != len(set(ids)):
            raise CanvasReadError("Canvas returned duplicate assignment IDs.")

        return assignments
