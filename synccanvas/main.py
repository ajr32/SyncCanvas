
"""SyncCanvas local-only prototype.

Do not expose publicly without authentication.
"""

from __future__ import annotations

from dataclasses import asdict

from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import RedirectResponse

from synccanvas.database import db
from synccanvas.pages import router as pages_router, today
from synccanvas.services.background_sync import background_sync
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

        # Preserve existing tasks.
        set_checkin(
            conn,
            class_id,
            nothing=True,
        )

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


# Background synchronization API.
# No Canvas worker is configured by default.


@app.get("/api/sync/status")
def sync_status():
    """Read the current background synchronization status."""
    return asdict(background_sync.status())


@app.post("/api/sync/run")
def sync_run():
    """Request one background synchronization attempt."""
    return asdict(background_sync.request_sync())


# Register the student and parent pages.
app.include_router(pages_router)
