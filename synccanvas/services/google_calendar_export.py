
"""Export SyncCanvas assignments to Google class calendars.

Uses parent planning dates when available, otherwise Canvas due dates.
Reflects SyncCanvas completion status with a checkmark in event titles.
Preview by default. Never modifies student progress or Canvas records.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from synccanvas.database import db
from synccanvas.services.family_time import family_today

MARKER_PREFIX = "SyncCanvas Canvas Course ID: "
EVENT_PREFIX = "sc"
DONE_PREFIX = "\u2713 "


@dataclass(frozen=True)
class ExportSummary:
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    skipped: int = 0


def event_id(course_id: int, assignment_id: int) -> str:
    """Return a stable Google-compatible event ID."""
    if course_id <= 0 or assignment_id <= 0:
        raise ValueError("Invalid assignment identifiers.")

    return (
        EVENT_PREFIX
        + format(course_id, "x")
        + "a"
        + format(assignment_id, "x")
    )


def load_assignments():
    """Load upcoming assignments using the family's effective date."""
    today = family_today().isoformat()

    with db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS canvas_family_planning (
                assignment_id INTEGER PRIMARY KEY,
                planning_date TEXT,
                show_now INTEGER NOT NULL DEFAULT 0
            )
            """
        )

        return conn.execute(
            """
            SELECT
                a.id,
                a.canvas_course_id,
                a.canvas_assignment_id,
                a.title,
                a.due_date,
                a.completed,
                fp.planning_date,
                COALESCE(
                    NULLIF(fp.planning_date, ''),
                    a.due_date
                ) AS calendar_date,
                a.html_url
            FROM canvas_assignments AS a
            LEFT JOIN canvas_family_planning AS fp
                ON fp.assignment_id = a.id
            JOIN canvas_course_links AS l
                ON l.canvas_course_id = a.canvas_course_id
            JOIN classes AS c
                ON c.id = l.class_id
            WHERE c.enabled = 1
              AND c.archived = 0
              AND a.missing_from_canvas = 0
              AND COALESCE(
                    NULLIF(fp.planning_date, ''),
                    a.due_date
                  ) >= ?
            ORDER BY
                a.canvas_course_id,
                calendar_date,
                a.title
            """,
            (today,),
        ).fetchall()


def find_calendars(service):
    """Find parent-owned SyncCanvas class calendars."""
    calendars = {}
    token = None

    while True:
        page = service.calendarList().list(
            pageToken=token,
            maxResults=250,
        ).execute(num_retries=3)

        for entry in page.get("items", []):
            if entry.get("accessRole") != "owner":
                continue

            details = service.calendars().get(
                calendarId=entry["id"]
            ).execute(num_retries=3)

            description = details.get("description", "")
            if not description.startswith(MARKER_PREFIX):
                continue

            course_id = description[len(MARKER_PREFIX):].strip()

            if course_id in calendars:
                raise RuntimeError(
                    f"Duplicate calendars for Canvas course {course_id}"
                )

            calendars[course_id] = entry["id"]

        token = page.get("nextPageToken")
        if not token:
            break

    return calendars


def build_event(row):
    """Build an all-day event from the effective planning date."""
    day = date.fromisoformat(row["calendar_date"])

    description = "Imported from Canvas by SyncCanvas."

    if row["planning_date"]:
        description += "\nDate selected by parent in SyncCanvas."

        if row["due_date"]:
            description += (
                f"\nTeacher due date: {row['due_date']}"
            )
        else:
            description += "\nTeacher has not set a due date."
    else:
        description += "\nDate provided by Canvas."

    if row["html_url"]:
        description += f"\nCanvas: {row['html_url']}"

    # Completion is owned by SyncCanvas.
    # Do not change the original assignment title in the database.
    title = row["title"]

    if bool(row["completed"]):
        title = DONE_PREFIX + title

    return {
        "id": event_id(
            row["canvas_course_id"],
            row["canvas_assignment_id"],
        ),
        "summary": title,
        "description": description,
        "start": {"date": day.isoformat()},
        "end": {
            "date": (day + timedelta(days=1)).isoformat()
        },
        "extendedProperties": {
            "private": {
                "synccanvas_course_id": str(
                    row["canvas_course_id"]
                ),
                "synccanvas_assignment_id": str(
                    row["canvas_assignment_id"]
                ),
            }
        },
    }


def export_assignments(service, apply=False):
    """Preview or export without duplicating existing events."""
    from googleapiclient.errors import HttpError

    calendars = find_calendars(service)
    assignments = load_assignments()

    created = updated = unchanged = skipped = 0

    for row in assignments:
        calendar_id = calendars.get(
            str(row["canvas_course_id"])
        )

        if not calendar_id:
            print(
                f"SKIP (no class calendar): {row['title']}"
            )
            skipped += 1
            continue

        desired = build_event(row)
        eid = desired["id"]

        try:
            existing = service.events().get(
                calendarId=calendar_id,
                eventId=eid,
            ).execute(num_retries=3)
        except HttpError as exc:
            if exc.resp.status == 404:
                existing = None
            else:
                raise

        if existing is None:
            action = "CREATE" if apply else "WOULD CREATE"

            print(
                f"{action}: {row['title']} "
                f"({row['calendar_date']})"
            )

            if apply:
                service.events().insert(
                    calendarId=calendar_id,
                    body=desired,
                ).execute(num_retries=3)

            created += 1
            continue

        fields = (
            "summary",
            "description",
            "start",
            "end",
        )

        changed = any(
            existing.get(field) != desired.get(field)
            for field in fields
        )

        if changed:
            action = "UPDATE" if apply else "WOULD UPDATE"

            print(
                f"{action}: {row['title']} "
                f"({row['calendar_date']})"
            )

            if apply:
                service.events().patch(
                    calendarId=calendar_id,
                    eventId=eid,
                    body={
                        field: desired[field]
                        for field in fields
                    },
                ).execute(num_retries=3)

            updated += 1
        else:
            unchanged += 1

    return ExportSummary(
        created=created,
        updated=updated,
        unchanged=unchanged,
        skipped=skipped,
    )
