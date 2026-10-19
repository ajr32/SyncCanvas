
"""Connect Canvas reading, mapping, and SQLite storage.

The worker is explicitly configured. It never imports CanvasSync
or changes student-created planner entries.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from synccanvas.database import db
from synccanvas.services.canvas_mapping import map_assignments
from synccanvas.services.canvas_storage import import_canvas_assignments


@dataclass(frozen=True)
class CanvasImportSummary:
    courses_processed: int = 0
    added: int = 0
    updated: int = 0
    unchanged: int = 0


class CanvasImportWorker:
    """Import assignments for active, explicitly linked Canvas courses."""

    def __init__(
        self,
        fetch_assignments: Callable[[int], list[dict]],
    ) -> None:
        if not callable(fetch_assignments):
            raise ValueError("A Canvas assignment fetcher is required.")

        self._fetch_assignments = fetch_assignments
        self.last_summary: CanvasImportSummary | None = None

    def __call__(self) -> None:
        """Run one import, suitable for BackgroundSync."""
        self.run()

    def run(self) -> CanvasImportSummary:
        # Only enabled, non-archived planner classes are synchronized.
        # Canvas links and historical assignments are not removed.
        with db() as conn:
            course_ids = [
                row["canvas_course_id"]
                for row in conn.execute(
                    """
                    SELECT l.canvas_course_id
                    FROM canvas_course_links AS l
                    JOIN classes AS c
                        ON c.id = l.class_id
                    WHERE c.enabled = 1
                      AND c.archived = 0
                    ORDER BY l.canvas_course_id
                    """
                )
            ]

        # Fetch and validate all eligible courses before writing.
        prepared = []

        for course_id in course_ids:
            raw = self._fetch_assignments(course_id)
            mapped = map_assignments(raw, course_id)
            prepared.append((course_id, mapped))

        added = updated = unchanged = 0

        # Preserve the existing all-or-nothing import behavior.
        with db() as conn:
            for course_id, mapped in prepared:
                result = import_canvas_assignments(
                    conn, course_id, mapped
                )
                added += result.added_count
                updated += result.updated_count
                unchanged += result.unchanged_count

        # Only record success after every course has fetched and committed.
        with db() as conn:
            conn.execute("""INSERT INTO canvas_sync_audit(id,last_success_at)
                VALUES(1,CURRENT_TIMESTAMP)
                ON CONFLICT(id) DO UPDATE SET last_success_at=excluded.last_success_at""")

        summary = CanvasImportSummary(
            courses_processed=len(prepared),
            added=added,
            updated=updated,
            unchanged=unchanged,
        )
        self.last_summary = summary
        return summary
