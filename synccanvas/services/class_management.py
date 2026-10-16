
"""Parent-controlled class management for SyncCanvas.

This module does not contact Canvas. It manages local planner
classes while preserving student work and Canvas relationships.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass


class ClassManagementError(ValueError):
    """A requested class change cannot be completed safely."""


@dataclass(frozen=True)
class ManagedClass:
    id: int
    name: str
    enabled: bool
    archived: bool
    canvas_course_id: int | None


def list_classes(conn: sqlite3.Connection) -> list[ManagedClass]:
    """Return all classes, including disabled and archived ones."""
    rows = conn.execute(
        """
        SELECT
            c.id,
            c.name,
            c.enabled,
            c.archived,
            l.canvas_course_id
        FROM classes c
        LEFT JOIN canvas_course_links l
            ON l.class_id = c.id
        ORDER BY c.sort_order, c.id
        """
    ).fetchall()

    return [
        ManagedClass(
            id=row["id"],
            name=row["name"],
            enabled=bool(row["enabled"]),
            archived=bool(row["archived"]),
            canvas_course_id=row["canvas_course_id"],
        )
        for row in rows
    ]


def active_classes(conn: sqlite3.Connection) -> list[ManagedClass]:
    """Classes that should appear in the student's planner."""
    return [
        item
        for item in list_classes(conn)
        if item.enabled and not item.archived
    ]


def require_class(conn: sqlite3.Connection, class_id: int):
    row = conn.execute(
        "SELECT id FROM classes WHERE id=?",
        (class_id,),
    ).fetchone()

    if row is None:
        raise ClassManagementError("Class not found.")


def validate_name(name: str) -> str:
    if not isinstance(name, str):
        raise ClassManagementError("Invalid class name.")

    name = name.strip()

    if not 1 <= len(name) <= 80:
        raise ClassManagementError(
            "Class name must be 1–80 characters."
        )

    return name


def add_class(conn: sqlite3.Connection, name: str) -> int:
    """Create a manual class. Does not create a Canvas link."""
    name = validate_name(name)

    try:
        cursor = conn.execute(
            "INSERT INTO classes(name) VALUES (?)",
            (name,),
        )
    except sqlite3.IntegrityError as error:
        raise ClassManagementError(
            "A class with that name already exists."
        ) from error

    return cursor.lastrowid


def rename_class(
    conn: sqlite3.Connection,
    class_id: int,
    name: str,
) -> None:
    require_class(conn, class_id)
    name = validate_name(name)

    try:
        conn.execute(
            "UPDATE classes SET name=? WHERE id=?",
            (name, class_id),
        )
    except sqlite3.IntegrityError as error:
        raise ClassManagementError(
            "A class with that name already exists."
        ) from error


def set_enabled(
    conn: sqlite3.Connection,
    class_id: int,
    enabled: bool,
) -> None:
    require_class(conn, class_id)

    conn.execute(
        "UPDATE classes SET enabled=? WHERE id=?",
        (int(enabled), class_id),
    )


def set_archived(
    conn: sqlite3.Connection,
    class_id: int,
    archived: bool,
) -> None:
    require_class(conn, class_id)

    conn.execute(
        "UPDATE classes SET archived=? WHERE id=?",
        (int(archived), class_id),
    )


def move_class(
    conn: sqlite3.Connection,
    class_id: int,
    direction: str,
) -> None:
    """Move a class up or down without changing its identity.

    The class order is stored in the existing sort_order column.
    Student entries, check-ins, and Canvas links are untouched.
    """
    require_class(conn, class_id)

    if direction not in ("up", "down"):
        raise ClassManagementError("Invalid move direction.")

    classes = list_classes(conn)
    ids = [item.id for item in classes]
    position = ids.index(class_id)

    target = position + (-1 if direction == "up" else 1)

    if target < 0 or target >= len(ids):
        return

    ids[position], ids[target] = ids[target], ids[position]

    for index, current_id in enumerate(ids):
        conn.execute(
            "UPDATE classes SET sort_order=? WHERE id=?",
            (index, current_id),
        )


def delete_empty_class(
    conn: sqlite3.Connection,
    class_id: int,
) -> None:
    """Delete only a completely unused, unlinked class.

    Historical tasks, check-ins, and Canvas relationships
    must never be removed as a side effect.
    """
    require_class(conn, class_id)

    checks = (
        ("entries", "class_id"),
        ("checkins", "class_id"),
        ("canvas_course_links", "class_id"),
    )

    for table, column in checks:
        row = conn.execute(
            f"SELECT 1 FROM {table} WHERE {column}=? LIMIT 1",
            (class_id,),
        ).fetchone()

        if row is not None:
            raise ClassManagementError(
                "This class has history or a Canvas link. "
                "Archive or disable it instead."
            )

    conn.execute(
        "DELETE FROM classes WHERE id=?",
        (class_id,),
    )
