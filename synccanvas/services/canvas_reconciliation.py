
"""Safe, read-only reconciliation of Canvas assignments with planner records.

Canvas owns assignment titles, descriptions, and due dates.
SyncCanvas owns student notes, completion status, and personal tasks.

This module calculates proposed changes; it performs no database writes.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable

from synccanvas.services.canvas_mapping import MappedAssignment


class ReconciliationError(ValueError):
    """An import cannot safely be reconciled."""


@dataclass(frozen=True)
class PlannerAssignment:
    """A planner record linked to an imported Canvas assignment."""

    canvas_id: int
    course_id: int
    title: str
    description: str = ""
    due_at: str | None = None
    due_date: str | None = None
    html_url: str | None = None

    # Student-owned fields: never replaced by a Canvas import.
    student_notes: str = ""
    completed: bool = False

    source: str = "canvas"
    submission_types: tuple[str, ...] = ()


@dataclass(frozen=True)
class ReconciliationResult:
    """A proposed complete collection, plus a change summary."""

    records: tuple[PlannerAssignment, ...]
    added: tuple[PlannerAssignment, ...]
    updated: tuple[PlannerAssignment, ...]
    unchanged: tuple[PlannerAssignment, ...]

    @property
    def added_count(self) -> int:
        return len(self.added)

    @property
    def updated_count(self) -> int:
        return len(self.updated)

    @property
    def unchanged_count(self) -> int:
        return len(self.unchanged)


def _key(course_id: int, canvas_id: int) -> tuple[int, int]:
    if (
        isinstance(course_id, bool)
        or not isinstance(course_id, int)
        or course_id <= 0
        or isinstance(canvas_id, bool)
        or not isinstance(canvas_id, int)
        or canvas_id <= 0
    ):
        raise ReconciliationError("Invalid Canvas assignment identity.")

    return course_id, canvas_id


def _new_record(item: MappedAssignment) -> PlannerAssignment:
    return PlannerAssignment(
        canvas_id=item.canvas_id,
        course_id=item.course_id,
        title=item.title,
        description=item.description,
        due_at=item.due_at,
        due_date=item.due_date,
        html_url=item.html_url,
        submission_types=item.submission_types,
    )


def _update_record(
    existing: PlannerAssignment,
    incoming: MappedAssignment,
) -> PlannerAssignment:
    """Replace only Canvas-owned fields."""
    return replace(
        existing,
        title=incoming.title,
        description=incoming.description,
        due_at=incoming.due_at,
        due_date=incoming.due_date,
        html_url=incoming.html_url,
        submission_types=incoming.submission_types,
    )


def reconcile_assignments(
    existing: Iterable[PlannerAssignment],
    incoming: Iterable[MappedAssignment],
) -> ReconciliationResult:
    """Plan an idempotent import without modifying either input.

    Matching uses (course_id, canvas_id), never assignment titles.
    Missing Canvas assignments are retained, not automatically deleted.
    """

    current = tuple(existing)
    imported = tuple(incoming)

    existing_by_key: dict[tuple[int, int], PlannerAssignment] = {}

    for record in current:
        if not isinstance(record, PlannerAssignment):
            raise ReconciliationError("Invalid existing assignment.")

        if record.source != "canvas":
            raise ReconciliationError(
                "Only Canvas-linked records belong in reconciliation."
            )

        identity = _key(record.course_id, record.canvas_id)

        if identity in existing_by_key:
            raise ReconciliationError(
                "Duplicate existing Canvas assignment identity."
            )

        existing_by_key[identity] = record

    incoming_by_key: dict[tuple[int, int], MappedAssignment] = {}

    for item in imported:
        if not isinstance(item, MappedAssignment):
            raise ReconciliationError("Invalid imported assignment.")

        if item.source != "canvas":
            raise ReconciliationError("Unexpected assignment source.")

        identity = _key(item.course_id, item.canvas_id)

        if identity in incoming_by_key:
            raise ReconciliationError(
                "Duplicate incoming Canvas assignment identity."
            )

        incoming_by_key[identity] = item

    result_by_key = dict(existing_by_key)
    added: list[PlannerAssignment] = []
    updated: list[PlannerAssignment] = []
    unchanged: list[PlannerAssignment] = []

    for identity, item in incoming_by_key.items():
        previous = existing_by_key.get(identity)

        if previous is None:
            record = _new_record(item)
            added.append(record)
        else:
            record = _update_record(previous, item)

            if record == previous:
                unchanged.append(record)
            else:
                updated.append(record)

        result_by_key[identity] = record

    return ReconciliationResult(
        records=tuple(result_by_key.values()),
        added=tuple(added),
        updated=tuple(updated),
        unchanged=tuple(unchanged),
    )
