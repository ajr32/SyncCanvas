
"""SyncCanvas local-only prototype.

Do not expose publicly without authentication.
"""

from __future__ import annotations

from dataclasses import asdict
import os

from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import RedirectResponse

from synccanvas.canvas_settings import get_canvas_settings
from synccanvas.database import db
from synccanvas.pages import router as pages_router, today
from synccanvas.parent_classes import router as parent_classes_router
from synccanvas.services.background_sync import background_sync
from synccanvas.services.canvas_http import CanvasHTTP
from synccanvas.services.canvas_import_worker import CanvasImportWorker
from synccanvas.services.sync_coordinator import sync_coordinator
from synccanvas.services.parent_review import (
    ParentReviewError,
    confirm_task,
    return_task,
    save_coaching_note,
)
from synccanvas.services.tasks import (
    TaskInput,
    validate_task,
    validate_task_details,
)


app = FastAPI(title="SyncCanvas (local prototype)")


def configure_canvas_sync(settings=None) -> bool:
    """Configure the existing shared Canvas synchronization service."""
    if settings is None:
        url, token = get_canvas_settings()
    else:
        url = settings.get("SYNCCANVAS_CANVAS_URL", "").strip()
        token = settings.get("SYNCCANVAS_CANVAS_TOKEN", "").strip()

    if not url or not token:
        return False

    try:
        client = CanvasHTTP(base_url=url, token=token)
    except ValueError:
        return False

    background_sync.configure(
        CanvasImportWorker(
            fetch_assignments=client.assignments_for_course
        )
    )
    return True


# Configuration does not start a Canvas network request.
configure_canvas_sync()


def go(path: str = "/") -> RedirectResponse:
    return RedirectResponse(path, status_code=303)


def set_checkin(conn, class_id: int, nothing: bool = False):
    conn.execute(
        """
        INSERT INTO checkins(
            class_id, day, nothing_tonight
        )
        VALUES (?, ?, ?)
        ON CONFLICT(class_id, day)
        DO UPDATE SET
            nothing_tonight = excluded.nothing_tonight
        """,
        (class_id, today(), int(nothing)),
    )


def require_class(conn, class_id: int):
    exists = conn.execute(
        "SELECT 1 FROM classes WHERE id=?",
        (class_id,),
    ).fetchone()

    if not exists:
        raise HTTPException(404, "Class not found")


@app.post("/classes")
def add_class(name: str = Form(...)):
    """Legacy route retained for existing tests and integrations."""
    name = name.strip()

    if not 1 <= len(name) <= 80:
        raise HTTPException(
            422,
            "Class name must be 1–80 characters",
        )

    with db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO classes(name) VALUES (?)",
            (name,),
        )

    return go()


@app.post("/classes/{class_id}/entries")
def add_entry(
    class_id: int,
    kind: str = Form(...),
    details: str = Form(...),
):
    try:
        task = validate_task(
            TaskInput(
                class_id=class_id,
                kind=kind,
                details=details,
            )
        )
    except ValueError as error:
        raise HTTPException(
            422, str(error)
        ) from error

    with db() as conn:
        require_class(conn, task.class_id)

        conn.execute(
            """
            INSERT INTO entries(
                class_id, kind, details
            )
            VALUES (?, ?, ?)
            """,
            (
                task.class_id,
                task.kind,
                task.details,
            ),
        )

        set_checkin(conn, task.class_id)

    return go()


@app.post("/classes/{class_id}/nothing")
def nothing_tonight(class_id: int):
    with db() as conn:
        require_class(conn, class_id)
        set_checkin(conn, class_id, nothing=True)

    return go()


@app.post("/classes/{class_id}/checkin")
def checked_today(class_id: int):
    with db() as conn:
        require_class(conn, class_id)
        set_checkin(conn, class_id)

    return go()


@app.post("/entries/{entry_id}/edit")
def edit_entry(
    entry_id: int,
    kind: str = Form(...),
    details: str = Form(...),
):
    try:
        kind, details = validate_task_details(
            kind, details
        )
    except ValueError as error:
        raise HTTPException(
            422, str(error)
        ) from error

    with db() as conn:
        result = conn.execute(
            """
            UPDATE entries
            SET kind=?, details=?
            WHERE id=?
              AND kind != 'Nothing Tonight'
            """,
            (kind, details, entry_id),
        )

        if result.rowcount == 0:
            raise HTTPException(
                404, "Entry not found"
            )

    return go()


@app.post("/entries/{entry_id}/toggle")
def toggle_entry(entry_id: int):
    with db() as conn:
        result = conn.execute(
            """
            UPDATE entries
            SET
                done=1-done,
                parent_confirmed=0
            WHERE id=?
              AND kind != 'Nothing Tonight'
            """,
            (entry_id,),
        )

        if result.rowcount == 0:
            raise HTTPException(
                404, "Entry not found"
            )

    return go()


@app.post("/parent/entries/{entry_id}/confirm")
def parent_confirm(entry_id: int):
    try:
        confirm_task(entry_id)
    except ParentReviewError as error:
        raise HTTPException(
            error.status_code,
            error.message,
        ) from error

    return go("/parent")


@app.post("/parent/entries/{entry_id}/return")
def parent_return(entry_id: int):
    try:
        return_task(entry_id)
    except ParentReviewError as error:
        raise HTTPException(
            error.status_code,
            error.message,
        ) from error

    return go("/parent")


@app.post("/parent/entries/{entry_id}/note")
def parent_note(entry_id: int, note: str = Form("")):
    try:
        save_coaching_note(entry_id, note)
    except ParentReviewError as error:
        raise HTTPException(
            error.status_code,
            error.message,
        ) from error

    return go("/parent")


@app.get("/api/sync/status")
def sync_status():
    return asdict(background_sync.status())


@app.post("/api/sync/run")
def sync_run():
    return asdict(background_sync.request_sync())


@app.post("/sync/run")
def sync_run_from_page():
    sync_coordinator.request_sync()
    return go("/")


app.include_router(pages_router)
app.include_router(parent_classes_router)
