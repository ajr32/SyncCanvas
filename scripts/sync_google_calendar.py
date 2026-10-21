
"""Preview or export SyncCanvas assignments to Google Calendar.

From the project root:

    python scripts/sync_google_calendar.py
    python scripts/sync_google_calendar.py --apply

Preview is the default. Only --apply writes events.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.setup_class_calendars import google_service
from synccanvas.services.google_calendar_export import (
    export_assignments,
)


def main():
    parser = argparse.ArgumentParser(
        description="Sync Canvas assignments to Google Calendar."
    )

    parser.add_argument(
        "--apply",
        action="store_true",
        help="Create or update Google Calendar events.",
    )

    args = parser.parse_args()

    print(
        "APPLY MODE - Google Calendar events may be modified."
        if args.apply
        else "PREVIEW ONLY - no Google Calendar events will be modified."
    )

    service = google_service()

    summary = export_assignments(
        service,
        apply=args.apply,
    )

    print("\nAssignment export summary:")
    print(f"  {'Created' if args.apply else 'Would create'}: {summary.created}")
    print(f"  {'Updated' if args.apply else 'Would update'}: {summary.updated}")
    print(f"  Unchanged: {summary.unchanged}")
    print(f"  Skipped: {summary.skipped}")

    if not args.apply:
        print("\nNo changes made. Review the preview before using --apply.")


if __name__ == "__main__":
    main()
