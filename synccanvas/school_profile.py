
"""Parent-managed school timezone and academic term dates.

GitMap #50. Local-only configuration; no Canvas or account changes.
"""

from datetime import date
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError, available_timezones

from fastapi import APIRouter, Form
from fastapi.responses import RedirectResponse

from synccanvas.database import db
from synccanvas.pages import esc, layout

router = APIRouter()

DEFAULT_TIMEZONE = "America/New_York"


def ensure_school_profile(conn):
    """Create the single-school configuration table if needed."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS school_profile (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            timezone TEXT NOT NULL,
            term_start TEXT,
            term_end TEXT,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        INSERT OR IGNORE INTO school_profile
            (id, timezone, term_start, term_end)
        VALUES (1, ?, NULL, NULL)
        """,
        (DEFAULT_TIMEZONE,),
    )


def read_school_profile(conn):
    ensure_school_profile(conn)
    return conn.execute(
        """
        SELECT timezone, term_start, term_end, updated_at
        FROM school_profile
        WHERE id = 1
        """
    ).fetchone()


def validate_timezone(value):
    value = value.strip()

    if not value or value not in available_timezones():
        raise ValueError("Choose a valid IANA timezone.")

    try:
        ZoneInfo(value)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(
            "Timezone data is unavailable. Install the tzdata package."
        ) from exc

    return value


def validate_date(value, label):
    value = value.strip()

    if not value:
        return None

    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(
            f"{label} must be a valid date."
        ) from exc

    if parsed.isoformat() != value:
        raise ValueError(
            f"{label} must use YYYY-MM-DD."
        )

    return parsed.isoformat()


def validate_profile(timezone, term_start, term_end):
    timezone = validate_timezone(timezone)
    start = validate_date(term_start, "Term start")
    end = validate_date(term_end, "Term end")

    if bool(start) != bool(end):
        raise ValueError(
            "Enter both term dates, or leave both empty."
        )

    if start and end and end < start:
        raise ValueError(
            "Term end must be on or after term start."
        )

    return timezone, start, end


def render_profile(error=None):
    with db() as conn:
        profile = read_school_profile(conn)

    timezone = esc(profile["timezone"])
    start = esc(profile["term_start"] or "")
    end = esc(profile["term_end"] or "")

    message = ""
    if error:
        message = (
            '<p role="alert" style="color:#a12636;font-weight:700">'
            f'{esc(error)}</p>'
        )

    content = f"""
    <section class="panel">
      <p><a href="/parent/school-days">← School Days</a></p>

      <h3>School profile</h3>

      <p>
        Set the school's timezone and the beginning and end
        of the current academic term.
      </p>

      {message}

      <form method="post" action="/parent/school-days/profile">
        <label for="school-timezone">School timezone</label>
        <input
          id="school-timezone"
          name="timezone"
          value="{timezone}"
          list="school-timezones"
          required
          style="width:100%;max-width:430px;box-sizing:border-box"
        >

        <datalist id="school-timezones">
          <option value="America/New_York">
          <option value="America/Chicago">
          <option value="America/Denver">
          <option value="America/Phoenix">
          <option value="America/Los_Angeles">
          <option value="America/Anchorage">
          <option value="Pacific/Honolulu">
        </datalist>

        <p><small>
          Examples: America/New_York, America/Chicago,
          America/Los_Angeles.
          Use a city-based timezone so daylight saving changes
          can be handled correctly.
        </small></p>

        <label for="term-start">Term begins</label>
        <input
          type="date"
          id="term-start"
          name="term_start"
          value="{start}"
        >

        <label for="term-end">Term ends</label>
        <input
          type="date"
          id="term-end"
          name="term_end"
          value="{end}"
        >

        <p><small>
          Enter both dates for the current term.
          Leave both empty if they are not known yet.
        </small></p>

        <button type="submit">Save school settings</button>
      </form>
    </section>

    <section class="panel">
      <h3>How these settings work</h3>
      <p>
        The settings are saved on this computer.
        Existing classes, school closures, assignments,
        and bell schedules are preserved.
      </p>
      <p>
        Timezone conversion and assignment scheduling will
        be connected in later issues.
      </p>
    </section>
    """

    return layout("School profile", content)


@router.get("/profile")
def profile_page():
    return render_profile()


@router.post("/profile")
def save_profile(
    timezone: str = Form(...),
    term_start: str = Form(""),
    term_end: str = Form(""),
):
    try:
        timezone, start, end = validate_profile(
            timezone, term_start, term_end
        )
    except ValueError as exc:
        response = render_profile(str(exc))
        response.status_code = 422
        return response

    with db() as conn:
        ensure_school_profile(conn)
        conn.execute(
            """
            UPDATE school_profile
            SET timezone = ?,
                term_start = ?,
                term_end = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = 1
            """,
            (timezone, start, end),
        )

    return RedirectResponse(
        "/parent/school-days/profile",
        status_code=303,
    )
