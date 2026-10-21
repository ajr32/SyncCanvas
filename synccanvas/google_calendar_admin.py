
"""Parent-facing Google Calendar controls for SyncCanvas."""

import ipaddress
from urllib.parse import urlsplit

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from synccanvas.pages import layout, esc

router = APIRouter(prefix="/parent/admin/google-calendar")

CALENDAR_URL = "/parent/admin/google-calendar"


def calendar_controls():
    return """
    <section class="panel">
      <h3>Google Calendar</h3>
      <p>Export assignments to your class calendars.
      Parent planning dates take priority over Canvas due dates.</p>

      <form method="post"
            action="/parent/admin/google-calendar/preview"
            class="inline">
        <button class="secondary" type="submit">
          Preview Changes
        </button>
      </form>

      <form method="post"
            action="/parent/admin/google-calendar/sync"
            class="inline"
            onsubmit="return confirm('Sync assignments to Google Calendar?');">
        <button type="submit">Sync Now</button>
      </form>
    </section>

    <section class="panel">
      <h3>Google Account Connection</h3>
      <p>Reconnect if Google authorization has expired or
      been revoked.</p>
      <p>This action must be started from the computer running
      SyncCanvas, using localhost. Google authorization will
      open in that computer's browser.</p>

      <form method="post"
            action="/parent/admin/google-calendar/reconnect"
            onsubmit="return confirm('Reconnect Google Calendar?');">
        <button class="secondary" type="submit">
          Reconnect Google Calendar
        </button>
      </form>
    </section>
    """


def calendar_error(exc):
    """Display errors without exposing credential details."""
    message = str(exc).lower()

    reconnect_needed = any(
        phrase in message
        for phrase in (
            "reconnect",
            "reconnected",
            "authorization has expired",
            "revoked",
            "authentication did not complete",
        )
    )

    if reconnect_needed:
        heading = "Reconnect Google Calendar"
        explanation = (
            "Google authorization needs attention. "
            "Open SyncCanvas on the server computer using "
            "localhost and select Reconnect Google Calendar."
        )
    else:
        heading = "Google Calendar connection unavailable"
        explanation = (
            "Check your network connection and Google "
            "credentials, then try again."
        )

    return layout(
        "Google Calendar",
        '<section class="panel" role="alert">'
        f"<h3>{esc(heading)}</h3>"
        f"<p>{esc(explanation)}</p>"
        "<p>Your SyncCanvas assignments and progress "
        "have not been changed by this connection error.</p>"
        f'<p><a href="{CALENDAR_URL}">'
        "Back to Google Calendar</a></p>"
        "</section>",
    )


def is_local_request(request: Request) -> bool:
    """Allow authorization only through a local browser.

    Checks both the connection peer and the requested hostname.
    Also rejects cross-origin browser submissions.
    """
    if request.client is None:
        return False

    try:
        peer = ipaddress.ip_address(request.client.host)
    except ValueError:
        return False

    if not peer.is_loopback:
        return False

    hostname = (request.url.hostname or "").lower()

    if hostname not in ("localhost", "127.0.0.1", "::1"):
        return False

    origin = request.headers.get("origin")
    if origin:
        try:
            parsed = urlsplit(origin)
            if (
                parsed.scheme != request.url.scheme
                or parsed.hostname != request.url.hostname
                or parsed.port != request.url.port
            ):
                return False
        except ValueError:
            return False

    if request.headers.get("sec-fetch-site") == "cross-site":
        return False

    return True


def run_export(apply: bool):
    from scripts.setup_class_calendars import google_service
    from synccanvas.services.google_calendar_export import (
        export_assignments,
    )

    try:
        service = google_service()
        result = export_assignments(service, apply=apply)
    except Exception as exc:
        return calendar_error(exc)

    heading = "Sync completed" if apply else "Preview completed"

    content = (
        '<section class="panel">'
        f"<h3>{esc(heading)}</h3>"
        f'<p>{"Created" if apply else "Would create"}: '
        f"{result.created}</p>"
        f'<p>{"Updated" if apply else "Would update"}: '
        f"{result.updated}</p>"
        f"<p>Unchanged: {result.unchanged}</p>"
        f"<p>Skipped: {result.skipped}</p>"
        f'<p><a href="{CALENDAR_URL}">'
        "Back to Google Calendar</a></p>"
        "</section>"
    )

    return layout("Google Calendar", content)


@router.get("", response_class=HTMLResponse)
def google_calendar_page():
    return layout("Google Calendar", calendar_controls())


@router.post("/preview", response_class=HTMLResponse)
def preview():
    return run_export(apply=False)


@router.post("/sync", response_class=HTMLResponse)
def sync():
    return run_export(apply=True)


@router.post("/reconnect", response_class=HTMLResponse)
def reconnect(request: Request):
    """Start Google authorization only from the server computer."""
    if not is_local_request(request):
        response = layout(
            "Google Calendar",
            '<section class="panel" role="alert">'
            "<h3>Reconnect unavailable on this device</h3>"
            "<p>Open SyncCanvas on the computer running "
            "the server using http://localhost:8000 "
            "and try again.</p>"
            f'<p><a href="{CALENDAR_URL}">Back</a></p>'
            "</section>",
        )
        response.status_code = 403
        return response

    from scripts.setup_class_calendars import (
        reconnect_google_calendar,
    )

    try:
        reconnect_google_calendar()
    except Exception as exc:
        return calendar_error(exc)

    return layout(
        "Google Calendar",
        '<section class="panel">'
        "<h3>Google Calendar reconnected</h3>"
        "<p>Authorization completed successfully.</p>"
        "<p>Your assignments and progress were not changed.</p>"
        "<p>You can now preview or synchronize "
        "your calendars.</p>"
        f'<p><a href="{CALENDAR_URL}">'
        "Back to Google Calendar</a></p>"
        "</section>",
    )
