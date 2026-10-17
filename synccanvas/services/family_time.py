"""Family-local calendar dates and timezone-aware Canvas due dates.

SYNCCANVAS_TIMEZONE may be set to an IANA zone (e.g. America/New_York).
If unset, the computer's configured local timezone is used. No UI setting.
"""
import os
from datetime import date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def family_timezone():
    name = os.environ.get("SYNCCANVAS_TIMEZONE", "").strip()
    if not name:
        return datetime.now().astimezone().tzinfo
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError(
            f"Invalid SYNCCANVAS_TIMEZONE {name!r}; use an IANA timezone "
            "such as America/New_York (install tzdata if required)."
        ) from exc


def family_today(now=None) -> date:
    """Date in the family's timezone, including DST transitions."""
    if now is None:
        now = datetime.now().astimezone()
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("A timezone-aware datetime is required.")
    return (now.astimezone(family_timezone()) if os.environ.get("SYNCCANVAS_TIMEZONE", "").strip() else now.astimezone()).date()


def canvas_due_date(value: str | None) -> str | None:
    """Interpret Canvas's offset-aware due_at as a family-local DATE.

    Preserve the original due_at string elsewhere; never mutate Canvas data.
    """
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Invalid Canvas due date.")
    try:
        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Invalid Canvas due date.") from exc
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ValueError("Canvas due date has no timezone.")
    local = moment.astimezone(family_timezone()) if os.environ.get("SYNCCANVAS_TIMEZONE", "").strip() else moment.astimezone()
    return local.date().isoformat()
