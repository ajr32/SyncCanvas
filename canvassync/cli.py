"""
CanvasSync command-line entry point.

One execution of this command represents one synchronization run.

In production, Google Cloud will execute this command on a schedule.
"""

from canvassync.canvas_client import (
    get_assignments_for_courses,
    get_courses,
    get_syncable_assignments,
    test_connection,
)

from canvassync.google_client import (
    get_or_create_course_calendar,
    sync_assignment_event,
)

import os

def main():
    """
    Run one CanvasSync synchronization cycle.
    """

    print()
    print("CanvasSync")
    print("==========")

    # Make sure Canvas is reachable before doing any work.
    if not test_connection():
        print()
        print("Canvas connection failed.")
        return

    # For now, use every active Canvas course automatically.
    #
    # Later we'll replace this with saved course configuration.
    courses = get_courses()

    print()
    print(f"Active courses: {len(courses)}")

    # Retrieve courses concurrently.
    assignments, failed_courses = get_assignments_for_courses(
        courses
    )

    print()
    print(f"Assignments retrieved: {len(assignments)}")

    # Never trust an incomplete Canvas result for destructive sync
    # operations. One failed course means we don't have a complete
    # picture of the user's assignments.
    if failed_courses:
        print()
        print(
            f"WARNING: {len(failed_courses)} course(s) "
            "could not be retrieved."
        )
        print(
            "Canvas data is incomplete. "
            "Destructive synchronization is disabled."
        )

    # Only assignments with due dates currently belong on the calendar.
    syncable = get_syncable_assignments(assignments)

    print(f"Assignments to sync: {len(syncable)}")

    google_accounts = [
        account.strip()
        for account in os.getenv("GOOGLE_ACCOUNTS", "").split(",")
        if account.strip()
    ]

    if not google_accounts:
        raise RuntimeError("No Google accounts configured.")

    # Connect to the dedicated CanvasSync Google Calendar. add
    print()
    print("Synchronizing Google Calendar...")

    for account in google_accounts:
        print()
        print(f"Google account: {account}")

        course_calendars = {}

        for assignment in syncable:
            course_id = assignment["course_id"]
            course_name = assignment["course_name"]

            if course_id not in course_calendars:
                course_calendars[course_id] = get_or_create_course_calendar(
                    account,
                    course_id,
                    course_name,
                )

            sync_assignment_event(
                account,
                course_calendars[course_id],
                assignment,
            )


if __name__ == "__main__":
    main()