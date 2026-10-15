
"""Read-only discovery of courses accessible to the Canvas account.

Discovery does not create classes, link courses, or import assignments.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from synccanvas.services.canvas_reader import CanvasReadError


@dataclass(frozen=True)
class DiscoveredCourse:
    canvas_course_id: int
    name: str
    course_code: str
    workflow_state: str


def discover_courses(
    fetch_courses: Callable[[], list[dict]],
) -> list[DiscoveredCourse]:
    """Return unique valid courses without guessing which are classes."""
    raw = fetch_courses()

    if not isinstance(raw, list):
        raise CanvasReadError(
            "Canvas returned an invalid course list."
        )

    result: list[DiscoveredCourse] = []
    seen: set[int] = set()

    for item in raw:
        if not isinstance(item, dict):
            raise CanvasReadError(
                "Canvas returned an invalid course entry."
            )

        course_id = item.get("id")

        if (
            isinstance(course_id, bool)
            or not isinstance(course_id, int)
            or course_id <= 0
        ):
            continue

        if course_id in seen:
            continue

        name = item.get("name")

        if not isinstance(name, str) or not name.strip():
            continue

        seen.add(course_id)

        result.append(
            DiscoveredCourse(
                canvas_course_id=course_id,
                name=name.strip(),
                course_code=str(
                    item.get("course_code") or ""
                ),
                workflow_state=str(
                    item.get("workflow_state") or ""
                ),
            )
        )

    return result


def discover_from_http(client) -> list[DiscoveredCourse]:
    """Use the existing HTTPS-only, paginated Canvas HTTP client."""
    return discover_courses(
        lambda: client.get_list(
            "/api/v1/courses?per_page=100"
        )
    )
