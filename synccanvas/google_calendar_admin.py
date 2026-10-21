"""Parent-facing Google Calendar controls for SyncCanvas."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from synccanvas.pages import layout, esc

router = APIRouter(prefix="/parent/admin/google-calendar")


def calendar_controls():
    return """
    <section class="panel">
      <h3>Google Calendar</h3>
      <p>Export assignments to your class calendars.
      Parent planning dates take priority over Canvas due dates.</p>

      <form method="post" action="/parent/admin/google-calendar/preview"
            class="inline">
        <button class="secondary" type="submit">Preview Changes</button>
      </form>

      <form method="post" action="/parent/admin/google-calendar/sync"
            class="inline"
            onsubmit="return confirm('Sync assignments to Google Calendar?');">
        <button type="submit">Sync Now</button>
      </form>
    </section>
    """


def run_export(apply: bool):
    from scripts.setup_class_calendars import google_service
    from synccanvas.services.google_calendar_export import export_assignments

    try:
        service = google_service()
        result = export_assignments(service, apply=apply)
    except Exception:
        return layout(
            "Google Calendar",
            '<section class="panel" role="alert">'
            '<h3>Google Calendar could not be reached</h3>'
            '<p>Check your local Google credentials and network connection. '
            'No SyncCanvas assignments were changed.</p>'
            '<p><a href="/parent/admin/google-calendar">Try again</a></p>'
            '</section>',
        )

    heading = "Sync completed" if apply else "Preview completed"

    content = (
        '<section class="panel">'
        f'<h3>{esc(heading)}</h3>'
        f'<p>{"Created" if apply else "Would create"}: {result.created}</p>'
        f'<p>{"Updated" if apply else "Would update"}: {result.updated}</p>'
        f'<p>Unchanged: {result.unchanged}</p>'
        f'<p>Skipped: {result.skipped}</p>'
        '<p><a href="/parent/admin/google-calendar">Back to Google Calendar</a></p>'
        '</section>'
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