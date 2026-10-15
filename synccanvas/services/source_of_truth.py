"""Source-of-truth rules for SyncCanvas (formerly CeeEss).

Canvas owns official school information.
SyncCanvas owns personal and family planning information.
CanvasSync owns its existing Google Calendar synchronization metadata.
"""

from enum import Enum
from typing import Any


class DataSource(str, Enum):
    CANVAS = "canvas"
    SYNCCANVAS = "synccanvas"
    CANVASSYNC = "canvassync"


class UnknownFieldError(ValueError):
    """Raised when ownership of a field is not defined."""


class SourceConflictError(ValueError):
    """Raised when a source attempts to change data it does not own."""


FIELD_OWNERS = {
    "assignment_title": DataSource.CANVAS,
    "assignment_description": DataSource.CANVAS,
    "assignment_due_date": DataSource.CANVAS,
    "assignment_status": DataSource.CANVAS,
    "course_name": DataSource.CANVAS,
    "canvas_assignment_id": DataSource.CANVAS,
    "student_notes": DataSource.SYNCCANVAS,
    "student_reminder": DataSource.SYNCCANVAS,
    "personal_task": DataSource.SYNCCANVAS,
    "parent_task": DataSource.SYNCCANVAS,
    "family_review_status": DataSource.SYNCCANVAS,
    "google_calendar_event_id": DataSource.CANVASSYNC,
    "calendar_sync_status": DataSource.CANVASSYNC,
}


def get_field_owner(field: str) -> DataSource:
    """Return the authoritative source for a field."""
    try:
        return FIELD_OWNERS[field]
    except KeyError as exc:
        raise UnknownFieldError(
            f"No source-of-truth rule exists for {field!r}"
        ) from exc


def can_update(field: str, source: DataSource | str) -> bool:
    """Check whether a source is allowed to update a field."""
    owner = get_field_owner(field)
    try:
        source = DataSource(source)
    except (ValueError, TypeError):
        return False
    return owner == source


def resolve_update(
    field: str,
    current_value: Any,
    new_value: Any,
    source: DataSource | str,
) -> Any:
    """Return an accepted update, or reject an unauthorized change.

    Does not write to the database or modify external systems.
    """
    owner = get_field_owner(field)

    if not can_update(field, source):
        raise SourceConflictError(
            f"{field!r} is owned by {owner.value}, "
            f"not {source!r}"
        )

    return new_value
