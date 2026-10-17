
"""Parent-managed dated school exceptions. No rotation-day support."""

from datetime import date

from fastapi import APIRouter, Form
from fastapi.responses import RedirectResponse

from synccanvas.database import db
from synccanvas.pages import esc, layout
from synccanvas.parent_schedule import normalize_time, display_time
from synccanvas.school_profile import router as profile_router

router = APIRouter(prefix="/parent/school-days")


def valid_day(value):
    try:
        parsed = date.fromisoformat(value)
    except (ValueError, TypeError):
        raise ValueError("Use a valid date (YYYY-MM-DD).")

    if parsed.isoformat() != value:
        raise ValueError("Use a valid date (YYYY-MM-DD).")

    return value


def problem(message):
    response = layout(
        "School day error",
        '<section class="panel"><p>'
        + esc(message)
        + '</p><a href="/parent/school-days">'
        + "Back to school days</a></section>",
    )
    response.status_code = 400
    return response


def back():
    return RedirectResponse(
        "/parent/school-days",
        status_code=303,
    )


@router.get("")
def index():
    with db() as conn:
        days = conn.execute(
            "SELECT * FROM school_days ORDER BY day DESC"
        ).fetchall()

        periods = conn.execute(
            """
            SELECT id, label, start_time, end_time
            FROM bell_periods
            ORDER BY start_time, id
            """
        ).fetchall()

        overrides = conn.execute(
            "SELECT * FROM school_day_periods"
        ).fetchall()

    overrides_by = {
        (r["day"], r["period_id"]): r
        for r in overrides
    }

    out = [
        '<section class="panel">',
        '<p><a href="/parent/schedule">← Bell Schedule</a></p>',
        '<h2>School settings</h2>',
        '<p>Configure your school timezone and term dates.</p>',
        '<p><a class="canvas-open" '
        'href="/parent/school-days/profile">'
        'Open School Profile</a></p>',
        '</section>',
        '<section class="panel">',
        '<h2>School closures and shortened days</h2>',
        '<p>Normal bell periods remain unchanged. '
        'Exceptions apply only to their selected date.</p>',
        '<form method="post" action="/parent/school-days/save">',
        '<label>Date <input type="date" name="day" required></label>',
        '<label>Type <select name="kind">',
        '<option value="closed">No school</option>',
        '<option value="shortened">'
        'Shortened / special schedule</option>',
        '</select></label>',
        '<label>Reason or note '
        '<input name="note" maxlength="200" '
        'placeholder="Holiday, early dismissal, etc."></label>',
        '<button>Save day</button></form></section>',
    ]

    for day in days:
        d = day["day"]
        kind = day["kind"]

        label = (
            "No school"
            if kind == "closed"
            else "Shortened day"
        )

        out.append(
            f'<section class="panel"><h3>{esc(d)} — '
            f'{label}</h3><p>{esc(day["note"])}</p>'
        )

        if kind == "shortened":
            out.append(
                "<p>Change individual period times below. "
                "Leave a period unchanged to use its normal time. "
                "Clear both time fields to remove an override.</p>"
            )

            for period in periods:
                pid = period["id"]
                ov = overrides_by.get((d, pid))

                start = (
                    display_time(ov["start_time"])
                    if ov else ""
                )
                end = (
                    display_time(ov["end_time"])
                    if ov else ""
                )

                out.append(
                    f'<form method="post" '
                    f'action="/parent/school-days/{d}/period/{pid}" '
                    'class="row">'
                    f'<strong>Period {esc(period["label"])} '
                    f'({esc(display_time(period["start_time"]))}'
                    f'–{esc(display_time(period["end_time"]))})'
                    '</strong>'
                    f'<input name="start_time" '
                    f'aria-label="New start" '
                    f'placeholder="New start" value="{esc(start)}">'
                    f'<input name="end_time" '
                    f'aria-label="New end" '
                    f'placeholder="New end" value="{esc(end)}">'
                    '<button>Save time</button></form>'
                )

        out.append(
            f'<form method="post" '
            f'action="/parent/school-days/{d}/delete">'
            '<button class="danger">'
            'Remove exception</button></form></section>'
        )

    return layout("School days", "".join(out))


@router.post("/save")
def save(
    day: str = Form(...),
    kind: str = Form(...),
    note: str = Form(""),
):
    try:
        valid_day(day)

        if kind not in ("closed", "shortened"):
            raise ValueError("Invalid school day type.")

        if len(note.strip()) > 200:
            raise ValueError("Note is too long.")

        with db() as conn:
            previous = conn.execute(
                "SELECT kind FROM school_days WHERE day=?",
                (day,),
            ).fetchone()

            conn.execute(
                """
                INSERT INTO school_days(day,kind,note)
                VALUES(?,?,?)
                ON CONFLICT(day) DO UPDATE SET
                    kind=excluded.kind,
                    note=excluded.note
                """,
                (day, kind, note.strip()),
            )

            if kind == "closed" or (
                previous and previous["kind"] != "shortened"
            ):
                conn.execute(
                    "DELETE FROM school_day_periods WHERE day=?",
                    (day,),
                )

    except ValueError as exc:
        return problem(str(exc))

    return back()


@router.post("/{day}/period/{period_id}")
def set_period(
    day: str,
    period_id: int,
    start_time: str = Form(""),
    end_time: str = Form(""),
):
    try:
        valid_day(day)

        with db() as conn:
            exists = conn.execute(
                """
                SELECT 1 FROM school_days
                WHERE day=? AND kind='shortened'
                """,
                (day,),
            ).fetchone()

            period = conn.execute(
                "SELECT 1 FROM bell_periods WHERE id=?",
                (period_id,),
            ).fetchone()

            if not exists or not period:
                raise ValueError(
                    "Shortened day or period not found."
                )

            if not start_time.strip() and not end_time.strip():
                conn.execute(
                    """
                    DELETE FROM school_day_periods
                    WHERE day=? AND period_id=?
                    """,
                    (day, period_id),
                )
            else:
                if not start_time.strip() or not end_time.strip():
                    raise ValueError(
                        "Enter both times, or leave both empty."
                    )

                start = normalize_time(start_time)
                end = normalize_time(end_time)

                if start >= end:
                    raise ValueError(
                        "End time must be after start time."
                    )

                conn.execute(
                    """
                    INSERT INTO school_day_periods(
                        day,period_id,start_time,end_time
                    )
                    VALUES(?,?,?,?)
                    ON CONFLICT(day,period_id) DO UPDATE SET
                        start_time=excluded.start_time,
                        end_time=excluded.end_time
                    """,
                    (day, period_id, start, end),
                )

    except ValueError as exc:
        return problem(str(exc))

    return back()


@router.post("/{day}/delete")
def delete(day: str):
    try:
        valid_day(day)
    except ValueError as exc:
        return problem(str(exc))

    with db() as conn:
        conn.execute(
            "DELETE FROM school_days WHERE day=?",
            (day,),
        )

    return back()


def school_day(conn, day):
    try:
        return conn.execute(
            "SELECT kind,note FROM school_days WHERE day=?",
            (day,),
        ).fetchone()
    except Exception as exc:
        if "no such table" not in str(exc):
            raise
        return None


# Register school-profile routes under /parent/school-days.
router.include_router(profile_router)
