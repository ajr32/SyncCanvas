"""
Canvas API client.

This module handles communication between CanvasSync and the Canvas API.

For now it can:
- authenticate with Canvas
- verify the current user
- retrieve the user's active courses

Later we'll add assignment retrieval here as well.
"""

import requests
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from canvassync.config import CANVAS_BASE_URL, CANVAS_TOKEN


# Headers sent with every Canvas API request.
#
# Canvas uses the access token as a Bearer token to identify the user
# making the request.
HEADERS = {
    "Authorization": f"Bearer {CANVAS_TOKEN}",
}


def test_connection():
    """
    Test the Canvas API connection.

    Requests the currently authenticated Canvas user. This gives us a
    simple way to verify that:

    - the Canvas URL is correct
    - the token exists
    - the token is valid
    - Canvas is accepting API requests

    Returns:
        True if the connection succeeds.
        False if the connection fails.
    """

    try:
        response = requests.get(
            f"{CANVAS_BASE_URL}/api/v1/users/self",
            headers=HEADERS,
            timeout=10,
        )

        # Turn HTTP error responses such as 401 or 403 into exceptions
        # that we can handle below.
        response.raise_for_status()

    except requests.exceptions.HTTPError as error:
        # 401 normally means Canvas did not accept the token.
        if error.response.status_code == 401:
            print(
                "Canvas authentication failed. "
                "Check your access token."
            )

        # 403 means Canvas understood who we are but denied access.
        elif error.response.status_code == 403:
            print(
                "Canvas denied access to this request."
            )

        # Handle any other HTTP error without crashing the program.
        else:
            print(
                "Canvas returned an error: "
                f"{error.response.status_code}"
            )

        return False

    except requests.exceptions.RequestException as error:
        # This catches network errors, timeouts, connection failures,
        # DNS problems, and similar situations.
        print(f"Could not connect to Canvas: {error}")
        return False

    # Canvas returned JSON describing the authenticated user.
    user = response.json()

    print(f"Connected to Canvas as: {user['name']}")

    return True


def get_courses():
    """
    Retrieve the user's active Canvas courses.

    Canvas's /api/v1/courses endpoint returns courses associated with
    the authenticated user.

    Returns:
        A list containing the course data returned by Canvas.
    """

    response = requests.get(
        f"{CANVAS_BASE_URL}/api/v1/courses",
        headers=HEADERS,

        # Ask Canvas for active enrollments.
        #
        # per_page=100 reduces the chance that a normal student account
        # requires multiple pages of results. We will add proper Canvas
        # pagination handling later.
        params={
            "enrollment_state": "active",
            "per_page": 100,
        },

        timeout=10,
    )

    # For now, raise an error if course retrieval fails.
    #
    # Later we'll move our common Canvas error handling into one reusable
    # request function so test_connection(), get_courses(), and
    # get_assignments() don't duplicate the same logic.
    response.raise_for_status()

    return response.json()

def parse_canvas_datetime(value):
    """
    Convert a Canvas ISO timestamp into a timezone-aware datetime.

    Canvas normally returns timestamps in UTC, for example:

        2026-08-28T16:30:00Z

    CanvasSync converts them to the local timezone rather than
    manually subtracting hours. This also handles daylight-saving
    time correctly.
    """

    if not value:
        return None

    utc_time = datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )

    local_timezone = ZoneInfo("America/New_York")

    return utc_time.astimezone(local_timezone)

def get_assignments(course_id):
    """
    Retrieve assignments for a Canvas course.

    Args:
        course_id:
            The Canvas ID of the course whose assignments we want.

    Returns:
        A list containing the assignment data returned by Canvas.
    """

    response = requests.get(
        f"{CANVAS_BASE_URL}/api/v1/courses/{course_id}/assignments",
        headers=HEADERS,
        params={
            "per_page": 100,
        },
        timeout=10,
    )

    response.raise_for_status()

    return response.json()

def get_assignments_for_courses(courses):
    """
    Retrieve assignments for all selected Canvas courses.

    Each returned assignment is given basic course information so later
    parts of CanvasSync know which Google Calendar it belongs to.
    """

    all_assignments = []

    for course in courses:
        course_id = course.get("id")
        course_name = course.get("name", "(Unnamed Course)")

        assignments = get_assignments(course_id)

        for assignment in assignments:
            # Add our own course information to the Canvas assignment
            # data. This makes it easy to determine where the assignment
            # belongs later.
            assignment["course_id"] = course_id
            assignment["course_name"] = course_name

            all_assignments.append(assignment)

    return all_assignments

def summarize_assignment_states(assignments):
    """
    Inspect the assignment states returned by Canvas.

    This is development output that helps us decide which assignments
    should eventually be synchronized to Google Calendar.
    """

    now = datetime.now(timezone.utc)

    published = 0
    unpublished = 0
    locked = 0
    no_due_date = 0
    past_due = 0
    future_due = 0

    for assignment in assignments:
        # Canvas tells us whether the assignment is published.
        if assignment.get("published", False):
            published += 1
        else:
            unpublished += 1

        due_at = assignment.get("due_at")
        unlock_at = assignment.get("unlock_at")

        # Assignments without a due date need special handling because
        # there is no obvious place to put them on Google Calendar.
        if due_at is None:
            no_due_date += 1
        else:
            due_date = datetime.fromisoformat(
                due_at.replace("Z", "+00:00")
            )

            if due_date < now:
                past_due += 1
            else:
                future_due += 1

        # An assignment is currently locked if its unlock time is still
        # in the future.
        if unlock_at is not None:
            unlock_date = datetime.fromisoformat(
                unlock_at.replace("Z", "+00:00")
            )

            if unlock_date > now:
                locked += 1

    print()
    print("Assignment States")
    print("-----------------")
    print(f"Published:      {published}")
    print(f"Unpublished:    {unpublished}")
    print(f"Locked:         {locked}")
    print(f"No due date:    {no_due_date}")
    print(f"Past due:       {past_due}")
    print(f"Future due:     {future_due}")

def should_sync_assignment(assignment):
    """
    Decide whether a Canvas assignment belongs on Google Calendar.

    Current rules:

    - The assignment must have a due date.
    - Locked assignments ARE included if they have a due date.
    - Assignments without due dates are ignored.

    Canvas courses often contain assignments or module content that
    teachers have prepared in advance but have not scheduled yet.
    Those items should not appear on Google Calendar until a due date
    is assigned.
    """

    due_at = assignment.get("due_at")

    if not due_at:
        return False

    return True

def get_syncable_assignments(assignments):
    """
    Return only assignments that should appear on Google Calendar.
    """

    return [
        assignment
        for assignment in assignments
        if should_sync_assignment(assignment)
    ]

def print_assignments(assignments):
    """
    Display the Canvas assignment information that will eventually
    be used to create Google Calendar events.
    """

    print()
    print("Canvas Assignments")
    print("------------------")

    for assignment in assignments:
        assignment_id = assignment.get("id")
        assignment_name = assignment.get(
            "name",
            "(Unnamed Assignment)",
        )

        # Canvas deadline.
        due_at = assignment.get("due_at")

        # When the assignment becomes available to the student.
        unlock_at = assignment.get("unlock_at")

        # When Canvas stops accepting access/submissions.
        lock_at = assignment.get("lock_at")

        # Direct browser link to the assignment.
        html_url = assignment.get("html_url")

        print()
        print(f"ID:        {assignment_id}")
        print(f"Name:      {assignment_name}")
        print(f"Due:       {due_at}")
        print(f"Unlock:    {unlock_at}")
        print(f"Lock:      {lock_at}")
        print(f"URL:       {html_url}")

def select_courses(courses):
    """
    Allow the user to choose which active Canvas courses to synchronize.

    Canvas may return active enrollments that are not normal academic
    classes, such as school resource courses. Rather than guessing which
    courses should be ignored, CanvasSync lets the user choose.
    """

    print()
    print("Select Courses")
    print("--------------")

    selected_courses = []

    for course in courses:
        course_id = course.get("id")
        course_name = course.get("name", "(Unnamed Course)")

        answer = input(
            f"Sync {course_name} ({course_id})? [Y/n]: "
        ).strip().lower()

        # Pressing Enter defaults to yes.
        if answer in ("", "y", "yes"):
            selected_courses.append(course)

    return selected_courses

def print_courses(courses):
    """
    Display a simple list of Canvas courses.

    This is primarily useful while we're developing CanvasSync.
    Eventually the course information will be used to create and map
    Google Calendars.
    """

    print()
    print("Canvas Courses")
    print("--------------")

    for course in courses:
        # Canvas courses have numeric IDs that we'll eventually use as
        # permanent identifiers when mapping courses to Google calendars.
        course_id = course.get("id")

        # Some Canvas course objects may not contain a name, so .get()
        # prevents a missing value from crashing this development output.
        course_name = course.get("name", "(Unnamed Course)")

        print(f"{course_id}: {course_name}")


def main():
    """
    Development entry point for the Canvas client.

    First verify authentication. If that succeeds, retrieve and display
    the active courses.
    """

    if not test_connection():
        return

    courses = get_courses()

    print_courses(courses)

    selected_courses = select_courses(courses)

    print()
    print(f"Selected {len(selected_courses)} courses.")


if __name__ == "__main__":
    if not test_connection():
        raise SystemExit(1)

    courses = get_courses()

    print_courses(courses)

    selected_courses = select_courses(courses)

    assignments = get_assignments_for_courses(selected_courses)

    print()
    print(f"Retrieved {len(assignments)} assignments.")
    summarize_assignment_states(assignments)

    syncable = get_syncable_assignments(assignments)

    print()
    print(f"Assignments to sync: {len(syncable)}")

    for assignment in syncable:
        due = parse_canvas_datetime(assignment.get("due_at"))
        unlock = parse_canvas_datetime(assignment.get("unlock_at"))
        lock = parse_canvas_datetime(assignment.get("lock_at"))

        print()
        print(f"Due:    {due}")
        print(f"Unlock: {unlock}")
        print(f"Lock:   {lock}")