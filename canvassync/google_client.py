"""
Google Calendar API client.

This module handles authentication with Google and creates an
authorized Google Calendar API service.

The first time CanvasSync runs, Google will ask the user to sign in
and approve access. After that, the authorization is saved locally
in token.json so future runs can authenticate automatically.
"""

from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import os
import json

from canvassync.config import (
    GOOGLE_CREDENTIALS_FILE,
    GOOGLE_TOKEN_FILE,
)


# CanvasSync needs permission to create and manage Google calendars
# and calendar events.
SCOPES = [
    "https://www.googleapis.com/auth/calendar",
]


def get_calendar_service():
    """
    Authenticate with Google and return a Calendar API service.

    On the first run:
        - opens the Google authorization flow
        - asks the user to approve CanvasSync
        - saves the resulting authorization to token.json

    On later runs:
        - loads token.json automatically
        - refreshes expired access tokens when possible
    """

    credentials = None

    token_path = Path(GOOGLE_TOKEN_FILE)
    credentials_path = Path(GOOGLE_CREDENTIALS_FILE)

    # In Google Cloud, OAuth credentials are supplied securely through
    # Secret Manager as an environment variable.
    google_token = os.getenv("GOOGLE_TOKEN")

    if google_token:
        credentials = Credentials.from_authorized_user_info(
            json.loads(google_token),
            SCOPES,
        )

    # If we've authorized CanvasSync before, load the saved credentials.
    if credentials is None and token_path.exists():
        credentials = Credentials.from_authorized_user_file(
            token_path,
            SCOPES,
        )

    # If there are no valid saved credentials, either refresh them
    # or start a new Google authorization flow.
    if not credentials or not credentials.valid:

        if (
            credentials
            and credentials.expired
            and credentials.refresh_token
        ):
            credentials.refresh(Request())

        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_path,
                SCOPES,
            )

            credentials = flow.run_local_server(
                port=0,
                access_type="offline",
                prompt="consent",
            )
        # Locally, save refreshed/new authorization for future runs.
        # In Google Cloud, GOOGLE_TOKEN comes from Secret Manager,
        # so don't try to replace it with a local file.
        if not google_token:
            token_path.write_text(
                credentials.to_json(),
                encoding="utf-8",
            )

    return build(
        "calendar",
        "v3",
        credentials=credentials,
    )
def get_or_create_course_calendar(course_id, course_name):
    """
    Return the Google Calendar belonging to one Canvas course.

    Each Canvas course gets its own calendar. The Canvas course ID is
    stored in the calendar description so CanvasSync can recognize the
    calendar even if the course name later changes.
    """

    service = get_calendar_service()

    calendar_name = f"CanvasSync - {course_name}"
    course_marker = f"CanvasSync Course ID: {course_id}"

    page_token = None

    while True:
        result = service.calendarList().list(
            pageToken=page_token,
        ).execute(num_retries=3)

        for calendar in result.get("items", []):
            calendar_id = calendar.get("id")

            # Get the full calendar details so we can inspect
            # the description containing our Canvas course ID.
            details = service.calendars().get(
                calendarId=calendar_id,
            ).execute(num_retries=3)

            if details.get("description") == course_marker:

                # If Canvas renamed the course, update the existing
                # Google Calendar instead of creating another one.
                if details.get("summary") != calendar_name:
                    details["summary"] = calendar_name

                    service.calendars().update(
                        calendarId=calendar_id,
                        body=details,
                    ).execute(num_retries=3)

                    print(f"Renamed calendar: {calendar_name}")

                else:
                    print(f"Found calendar: {calendar_name}")

                return calendar_id

        page_token = result.get("nextPageToken")

        if not page_token:
            break

    # No calendar exists for this Canvas course yet.
    calendar = service.calendars().insert(
        body={
            "summary": calendar_name,
            "description": course_marker,
            "timeZone": "America/New_York",
        },
    ).execute(num_retries=3)

    print(f"Created calendar: {calendar_name}")

    return calendar.get("id")

def sync_assignment_event(calendar_id, assignment):
    """
    Create or update one Canvas assignment in Google Calendar.

    The Canvas assignment ID is stored as private event metadata.
    That lets CanvasSync find the same event on future runs instead
    of creating duplicates.
    """

    service = get_calendar_service()

    assignment_id = str(assignment["id"])
    title = assignment["name"]

    due = assignment.get("due_at")

    if not due:
        return

    # Find an existing event created for this Canvas assignment.
    result = service.events().list(
        calendarId=calendar_id,
        privateExtendedProperty=f"canvas_assignment_id={assignment_id}",
        maxResults=1,
    ).execute(num_retries=3)

    existing_events = result.get("items", [])

    event_body = {
        "summary": title,
        "description": (
            f"Canvas course: {assignment.get('course_name', '')}\n"
            f"{assignment.get('html_url', '')}"
        ),
        "start": {
            "dateTime": due,
        },
        "end": {
            "dateTime": due,
        },
        "extendedProperties": {
            "private": {
                "canvas_assignment_id": assignment_id,
            }
        },
    }

    if existing_events:
        event_id = existing_events[0]["id"]

        service.events().update(
            calendarId=calendar_id,
            eventId=event_id,
            body=event_body,
        ).execute(num_retries=3)

        print(f"Updated: {title}")

    else:
        service.events().insert(
            calendarId=calendar_id,
            body=event_body,
        ).execute(num_retries=3)

        print(f"Created: {title}")

def create_test_calendar():
    """
    Create a dedicated Google Calendar for CanvasSync testing.

    Using a separate test calendar lets us safely experiment with
    creating and updating events without touching existing calendars.
    """

    service = get_calendar_service()

    calendar = {
        "summary": "CanvasSync Test",
        "timeZone": "America/New_York",
    }

    created_calendar = service.calendars().insert(
        body=calendar,
    ).execute(num_retries=3)

    print()
    print("Created test calendar:")
    print(f"Name: {created_calendar.get('summary')}")
    print(f"ID:   {created_calendar.get('id')}")

    return created_calendar

def test_connection():
    """
    Test Google Calendar access by retrieving the user's calendar list.
    """

    service = get_calendar_service()

    result = service.calendarList().list(
        maxResults=10,
    ).execute()

    calendars = result.get("items", [])

    print()
    print("Connected to Google Calendar.")
    print(f"Calendars found: {len(calendars)}")

    for calendar in calendars:
        print(f"- {calendar.get('summary')}")


if __name__ == "__main__":
    test_connection()