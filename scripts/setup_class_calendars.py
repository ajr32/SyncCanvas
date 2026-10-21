
"""Create Google Calendars for active SyncCanvas classes.

From the project root:

    python scripts/setup_class_calendars.py
    python scripts/setup_class_calendars.py --apply

Preview is the default. Only --apply can create calendars.

Only enabled, non-archived SyncCanvas classes with Canvas
links are eligible. Canvas-only courses are not imported.
"""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from synccanvas.database import db
from synccanvas.services.class_management import active_classes
from synccanvas.services.google_calendar_provisioning import (
    Course,
    ensure_course_calendars,
)


def google_service():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    scope = ["https://www.googleapis.com/auth/calendar"]

    token_path = ROOT / "synccanvas_google_token.json"
    credentials_path = ROOT / "synccanvas_google_credentials.json"

    credentials = None

    if token_path.is_file():
        credentials = Credentials.from_authorized_user_file(
            str(token_path),
            scope,
        )

    if (
        credentials
        and credentials.expired
        and credentials.refresh_token
    ):
        credentials.refresh(Request())

    elif not credentials or not credentials.valid:
        if not credentials_path.is_file():
            raise RuntimeError(
                f"Missing {credentials_path.name}. "
                "Download a Google OAuth Desktop client JSON "
                "from Google Cloud Console and save it in "
                "the project root."
            )

        flow = InstalledAppFlow.from_client_secrets_file(
            str(credentials_path),
            scope,
        )

        credentials = flow.run_local_server(
            port=0,
            access_type="offline",
            prompt="consent",
        )

    if not credentials.valid:
        raise RuntimeError(
            "Google authentication did not complete."
        )

    token_path.write_text(
        credentials.to_json(),
        encoding="utf-8",
    )

    return build(
        "calendar",
        "v3",
        credentials=credentials,
    )


def selected_courses():
    """Get active Canvas-linked classes from the local database."""

    with db() as conn:
        classes = active_classes(conn)

    courses = [
        Course(
            cls.canvas_course_id,
            cls.name,
        )
        for cls in classes
        if cls.canvas_course_id is not None
    ]

    return courses


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Create Google Calendars for active, "
            "Canvas-linked SyncCanvas classes."
        )
    )

    parser.add_argument(
        "--apply",
        action="store_true",
        help="Create missing Google calendars",
    )

    args = parser.parse_args()

    courses = selected_courses()

    print(
        f"Found {len(courses)} active Canvas-linked "
        "SyncCanvas classes."
    )

    print(
        "APPLY MODE"
        if args.apply
        else "PREVIEW ONLY - no calendars will be created"
    )

    if not courses:
        print(
            "No eligible classes found. "
            "Check Parent > Admin > Classes."
        )
        return

    service = google_service()

    results = ensure_course_calendars(
        service,
        courses,
        apply=args.apply,
    )

    for status, course_id, title, calendar_id in results:
        print(
            f"{status:12} "
            f"{course_id:>9}  "
            f"{title} "
            f"{calendar_id}"
        )

    if args.apply:
        print(
            "\nCalendar provisioning completed. "
            "Review Google Calendar settings before "
            "sharing calendars with Zachary."
        )
    else:
        print(
            "\nPreview complete. "
            "Run again with --apply only after "
            "confirming the course list."
        )


if __name__ == "__main__":
    main()
