"""Proposed Firestore layout for one family, not an active backend.

This is a data contract only. SQLite remains the current storage engine.
A future Firestore adapter must enforce family ownership on every read/write;
document paths alone are NOT authorization.
"""
from dataclasses import dataclass

SCHEMA_VERSION = 1
COLLECTIONS = {
    "families": ("display_name", "created_at", "schema_version"),
    "students": ("family_id", "display_name", "timezone"),
    "classes": ("family_id", "student_id", "name", "sort_order", "enabled", "archived"),
    "periods": ("family_id", "student_id", "label", "start_time", "end_time", "weekdays"),
    "entries": ("family_id", "student_id", "class_id", "kind", "details", "done", "due_date", "due_time", "priority", "origin", "planned_date", "parent_confirmed"),
    "school_days": ("family_id", "student_id", "day", "kind", "note"),
    "lunch_buddies": ("family_id", "student_id", "period_id", "name", "weekdays"),
    "lunch_tasks": ("family_id", "student_id", "activity_id", "details", "done", "parent_confirmed"),
    "canvas_assignments": ("family_id", "student_id", "canvas_course_id", "canvas_assignment_id", "title", "due_at", "due_date"),
}
# Composite indexes needed for planned query shapes; single-field indexes
# remain Firestore defaults unless deliberately disabled at deployment.
INDEXES = (
    ("classes", ("student_id", "enabled", "archived", "sort_order")),
    ("entries", ("student_id", "class_id", "done", "due_date")),
    ("school_days", ("student_id", "day")),
    ("canvas_assignments", ("student_id", "canvas_course_id", "canvas_assignment_id")),
)
def document_path(family_id: str, collection: str, document_id: str) -> str:
    """Construct a family-scoped document path; reject unsafe path segments."""
    if collection not in COLLECTIONS:
        raise ValueError("Unknown collection")
    for value in (family_id, document_id):
        if not isinstance(value, str) or not value or value in (".", "..") or "/" in value or len(value.encode("utf-8")) > 1500:
            raise ValueError("Invalid Firestore document path segment")
    return f"families/{family_id}/{collection}/{document_id}"
