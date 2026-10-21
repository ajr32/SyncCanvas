"""Provision one parent-owned Google Calendar per Canvas course, without assignments.

No Google calls are made until ensure_course_calendars is explicitly invoked.
"""
from __future__ import annotations

from dataclasses import dataclass

MARKER_PREFIX = "SyncCanvas Canvas Course ID: "
INITIALIZATION_EVENT_ID = "scinit2000"

@dataclass(frozen=True)
class Course:
    id: int
    name: str


def _calendar_marker(course_id: int) -> str:
    return f"{MARKER_PREFIX}{course_id}"


def _all_owned_calendars(service):
    token = None
    while True:
        result = service.calendarList().list(pageToken=token, maxResults=250).execute(num_retries=3)
        for entry in result.get("items", []):
            if entry.get("accessRole") == "owner":
                yield entry
        token = result.get("nextPageToken")
        if not token:
            break


def _lookup_by_marker(service):
    """Read descriptions, since calendarList entries may not contain them."""
    found = {}
    for entry in _all_owned_calendars(service):
        details = service.calendars().get(calendarId=entry["id"]).execute(num_retries=3)
        description = details.get("description", "")
        if description.startswith(MARKER_PREFIX):
            key = description[len(MARKER_PREFIX):]
            if key in found:
                raise RuntimeError(f"Duplicate SyncCanvas calendars for Canvas course {key}; resolve manually")
            found[key] = details
    return found


def _ensure_initialization_event(service, calendar_id):
    # Google Calendar permits a deterministic, valid event ID, making retry safe.
    # Event IDs allow lowercase a-v and digits 0-9.
    from googleapiclient.errors import HttpError
    body = {
        "id": INITIALIZATION_EVENT_ID,
        "summary": "SyncCanvas — Calendar Initialized",
        "description": "This calendar belongs to a Canvas course and is managed by SyncCanvas.",
        "start": {"date": "2000-01-01"},
        "end": {"date": "2000-01-02"},
        "transparency": "transparent",
    }
    try:
        service.events().insert(calendarId=calendar_id, body=body).execute(num_retries=3)
    except HttpError as exc:
        if getattr(exc.resp, "status", None) != 409:
            raise


def ensure_course_calendars(service, courses, apply=False):
    """Return actions. Preview by default; apply=True creates missing calendars.

    Existing calendars are discovered using their Canvas course ID marker.
    Does not share calendars, sync assignments, or remove historical calendars.
    """
    existing = _lookup_by_marker(service)
    results = []
    seen = set()
    for course in courses:
        if isinstance(course.id, bool) or not isinstance(course.id, int) or course.id <= 0:
            raise ValueError("Canvas course ID must be a positive integer")
        if not course.name.strip():
            raise ValueError("Canvas course name cannot be blank")
        key = str(course.id)
        if key in seen:
            continue
        seen.add(key)
        title = f"SyncCanvas — {course.name.strip()}"
        current = existing.get(key)
        if current is None:
            if apply:
                created = service.calendars().insert(body={
                    "summary": title,
                    "description": _calendar_marker(course.id),
                    "timeZone": "America/New_York",
                }).execute(num_retries=3)
                calendar_id = created["id"]
                # If the event fails, the calendar remains discoverable for a retry.
                _ensure_initialization_event(service, calendar_id)
                existing[key] = created
                results.append(("created", course.id, title, calendar_id))
            else:
                results.append(("would create", course.id, title, ""))
        else:
            calendar_id = current["id"]
            if apply:
                if current.get("summary") != title:
                    service.calendars().patch(calendarId=calendar_id, body={"summary": title}).execute(num_retries=3)
                _ensure_initialization_event(service, calendar_id)
            results.append(("existing", course.id, title, calendar_id))
    return results
