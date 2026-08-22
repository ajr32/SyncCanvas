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

    for assignment in syncable:
        print(
            f"  {assignment.get('course_name')}: "
            f"{assignment.get('name')}"
        )

    print()
    print("CanvasSync finished.")


if __name__ == "__main__":
    main()