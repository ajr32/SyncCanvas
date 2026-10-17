"""Parent-managed school bell schedule."""

import re
import sqlite3
from datetime import datetime

from fastapi import APIRouter, Form
from fastapi.responses import RedirectResponse

from synccanvas.database import db
from synccanvas.pages import layout, esc


router = APIRouter(prefix="/parent/schedule")

TIME = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")
DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def display_time(value):
    """Show stored 24-hour times as 12-hour AM/PM times."""
    return datetime.strptime(value, "%H:%M").strftime("%I:%M %p").lstrip("0")


def normalize_time(value):
    """Accept 12-hour entries and legacy 24-hour form submissions."""
    value = value.strip().upper().replace(".", "")
    for fmt in ("%I:%M %p", "%I:%M%p", "%H:%M"):
        try:
            return datetime.strptime(value, fmt).strftime("%H:%M")
        except ValueError:
            continue
    raise ValueError("Enter a time such as 8:15 AM or 1:30 PM.")


def back():
    return RedirectResponse("/parent/schedule", status_code=303)


def error(message):
    response = layout(
        "Schedule error",
        f'<section class="panel"><p>{esc(message)}</p>'
        '<p><a href="/parent/schedule">Back to schedule</a></p></section>',
    )
    response.status_code = 400
    return response


@router.get("")
def schedule():
    with db() as conn:
        periods = conn.execute(
            "SELECT * FROM bell_periods ORDER BY start_time,id"
        ).fetchall()

        classes = conn.execute(
            """
            SELECT id,name FROM classes
            WHERE enabled=1 AND archived=0
            ORDER BY sort_order,id
            """
        ).fetchall()

        assignments = conn.execute(
            "SELECT class_id,period_id FROM class_periods"
        ).fetchall()

    by_period = {}

    for assignment in assignments:
        by_period.setdefault(
            assignment["period_id"], set()
        ).add(assignment["class_id"])

    parts = [
        '<section class="panel">',
        '<p><a href="/parent">← Parent Page</a></p>',
        '<h3>Add a bell period</h3>',
        '<p><a href="/parent/school-days">Manage closures and shortened days →</a></p>',
        '<form method="post" action="/parent/schedule/add">',
        '<label>Period label (1–7, L, etc.)</label>',
        '<input name="label" maxlength="12" required>',
        '<label>Starts</label>',
        '<input type="text" name="start_time" placeholder="8:00 AM" required>',
        '<label>Ends</label>',
        '<input type="text" name="end_time" placeholder="8:50 AM" required>',
        '<p>Meeting days:</p>',
    ]

    for index, day in enumerate(DAYS):
        checked = "checked" if index < 5 else ""

        parts.append(
            '<label style="display:inline-block;margin-right:12px">'
            f'<input type="checkbox" name="days" value="{index}" '
            f'{checked}> {day}</label>'
        )

    parts.append(
        '<p><button type="submit">Add period</button></p>'
        '</form></section>'
    )

    for period in periods:
        period_id = period["id"]

        parts.append(
            '<section class="panel">'
            f'<h3>Period {esc(period["label"])} · '
            f'{esc(display_time(period["start_time"]))}–'
            f'{esc(display_time(period["end_time"]))}</h3>'
        )

        meeting_days = ", ".join(
            DAYS[int(day)] for day in period["weekdays"]
        )

        parts.append(f"<p>Days: {esc(meeting_days)}</p>")

        parts.append(
            '<form method="post" '
            f'action="/parent/schedule/{period_id}/update">'
            '<label>Label</label>'
            f'<input name="label" maxlength="12" required '
            f'value="{esc(period["label"])}">'
            '<label>Starts</label>'
            f'<input type="text" name="start_time" '
            f'value="{esc(display_time(period["start_time"]))}" required>'
            '<label>Ends</label>'
            f'<input type="text" name="end_time" '
            f'value="{esc(display_time(period["end_time"]))}" required>'
            '<p>Meeting days:</p>'
        )

        for index, day in enumerate(DAYS):
            checked = (
                "checked"
                if str(index) in period["weekdays"]
                else ""
            )

            parts.append(
                '<label style="display:inline-block;margin-right:12px">'
                f'<input type="checkbox" name="days" '
                f'value="{index}" {checked}> {day}</label>'
            )

        parts.append(
            '<p><button type="submit">Save period</button></p>'
            '</form>'
        )

        parts.append(
            f'<form method="post" '
            f'action="/parent/schedule/{period_id}/assign">'
            '<label>Assign classes or activities</label>'
        )

        assigned = by_period.get(period_id, set())

        for cls in classes:
            checked = (
                "checked"
                if cls["id"] in assigned
                else ""
            )

            parts.append(
                '<label>'
                f'<input type="checkbox" name="class_ids" '
                f'value="{cls["id"]}" {checked}> '
                f'{esc(cls["name"])}'
                '</label>'
            )

        parts.append(
            '<button type="submit">Save assignments</button>'
            '</form>'
        )

        parts.append(
            '<form method="post" '
            f'action="/parent/schedule/{period_id}/delete" '
            'onsubmit="return confirm('
            "'Delete this period and its assignments?');"
            '">'
            '<button class="danger">Delete period</button>'
            '</form></section>'
        )

    if not periods:
        parts.append(
            '<section class="panel">'
            '<p>No bell periods configured yet. '
            'Classes continue using their manual order.</p>'
            '</section>'
        )

    return layout("Bell Schedule", "".join(parts))


def validate(label, start_time, end_time, days):
    label = label.strip().upper()

    if not 1 <= len(label) <= 12:
        raise ValueError(
            "Period label must be 1–12 characters."
        )

    start_time = normalize_time(start_time)
    end_time = normalize_time(end_time)

    if start_time >= end_time:
        raise ValueError(
            "Enter valid times with the end after the start."
        )

    if not days or any(day not in "0123456" for day in days):
        raise ValueError(
            "Select at least one valid meeting day."
        )

    return (
        label,
        start_time,
        end_time,
        "".join(sorted(set(days))),
    )


@router.post("/add")
def add(
    label: str = Form(...),
    start_time: str = Form(...),
    end_time: str = Form(...),
    days: list[str] = Form([]),
):
    try:
        values = validate(
            label, start_time, end_time, days
        )

        with db() as conn:
            conn.execute(
                """
                INSERT INTO bell_periods(
                    label, start_time, end_time, weekdays
                )
                VALUES (?, ?, ?, ?)
                """,
                values,
            )

    except (ValueError, sqlite3.IntegrityError) as exc:
        return error(f"Could not add period: {exc}")

    return back()


@router.post("/{period_id}/update")
def update(
    period_id: int,
    label: str = Form(...),
    start_time: str = Form(...),
    end_time: str = Form(...),
    days: list[str] = Form([]),
):
    try:
        values = validate(
            label, start_time, end_time, days
        )

        with db() as conn:
            result = conn.execute(
                """
                UPDATE bell_periods
                SET label=?, start_time=?, end_time=?, weekdays=?
                WHERE id=?
                """,
                (*values, period_id),
            )

            if not result.rowcount:
                raise ValueError("Period not found.")

    except (ValueError, sqlite3.IntegrityError) as exc:
        return error(f"Could not update period: {exc}")

    return back()


@router.post("/{period_id}/assign")
def assign(
    period_id: int,
    class_ids: list[int] = Form([]),
):
    try:
        with db() as conn:
            exists = conn.execute(
                "SELECT 1 FROM bell_periods WHERE id=?",
                (period_id,),
            ).fetchone()

            if not exists:
                raise ValueError("Period not found.")

            allowed = {
                row["id"]
                for row in conn.execute(
                    """
                    SELECT id FROM classes
                    WHERE enabled=1 AND archived=0
                    """
                )
            }

            if not set(class_ids) <= allowed:
                raise ValueError(
                    "Unknown or inactive class."
                )

            conn.execute(
                "DELETE FROM class_periods WHERE period_id=?",
                (period_id,),
            )

            conn.executemany(
                """
                INSERT INTO class_periods(class_id,period_id)
                VALUES (?,?)
                """,
                [
                    (class_id, period_id)
                    for class_id in set(class_ids)
                ],
            )

    except (ValueError, sqlite3.IntegrityError) as exc:
        return error(f"Could not save assignments: {exc}")

    return back()


@router.post("/{period_id}/delete")
def delete(period_id: int):
    with db() as conn:
        conn.execute(
            "DELETE FROM bell_periods WHERE id=?",
            (period_id,),
        )

    return back()