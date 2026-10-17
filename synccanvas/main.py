"""SyncCanvas local-only prototype. Do not expose without authentication."""
from __future__ import annotations
from dataclasses import asdict
import sqlite3
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
from synccanvas.services.parent_review import ParentReviewError, confirm_task, return_task, save_coaching_note
from synccanvas.services.tasks import TaskInput, validate_task, validate_task_details
from synccanvas.parent_schedule import router as parent_schedule_router

app = FastAPI(title="SyncCanvas (local prototype)")

def configure_canvas_sync(settings=None) -> bool:
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
    background_sync.configure(CanvasImportWorker(fetch_assignments=client.assignments_for_course))
    return True

configure_canvas_sync()

def go(path="/"):
    return RedirectResponse(path, status_code=303)

def set_checkin(conn, class_id, nothing=False):
    conn.execute("""INSERT INTO checkins(class_id, day, nothing_tonight) VALUES (?, ?, ?)
        ON CONFLICT(class_id, day) DO UPDATE SET nothing_tonight=excluded.nothing_tonight""",
        (class_id, today(), int(nothing)))

def require_class(conn, class_id):
    if not conn.execute("SELECT 1 FROM classes WHERE id=?", (class_id,)).fetchone():
        raise HTTPException(404, "Class not found")

@app.post("/classes")
def add_class(name: str = Form(...)):
    name = name.strip()
    if not 1 <= len(name) <= 80:
        raise HTTPException(422, "Class name must be 1–80 characters")
    with db() as conn:
        conn.execute("INSERT OR IGNORE INTO classes(name) VALUES (?)", (name,))
    return go()

@app.post("/school/classes/{class_id}/review")
def school_review_class(class_id: int, outcome: str = Form(...)):
    if outcome not in ("reviewed", "nothing", "needs_followup"):
        raise HTTPException(422, "Invalid class review outcome")
    with db() as conn:
        require_class(conn, class_id)
        conn.execute("""INSERT INTO school_reviews(class_id,day,outcome)
            VALUES(?,?,?) ON CONFLICT(class_id,day) DO UPDATE SET
            outcome=excluded.outcome,reviewed_at=CURRENT_TIMESTAMP""",(class_id,today(),outcome))
    return go("/review")

@app.post("/school/papers")
def school_review_papers(pocket_checked: str = Form(""), backpack_checked: str = Form(""), notes: str = Form("")):
    if len(notes.strip()) > 300:
        raise HTTPException(422, "Paper notes must be at most 300 characters")
    with db() as conn:
        conn.execute("""INSERT INTO paper_reviews(day,pocket_checked,backpack_checked,notes)
            VALUES(?,?,?,?) ON CONFLICT(day) DO UPDATE SET
            pocket_checked=excluded.pocket_checked,backpack_checked=excluded.backpack_checked,
            notes=excluded.notes,reviewed_at=CURRENT_TIMESTAMP""",
            (today(),int(pocket_checked=="yes"),int(backpack_checked=="yes"),notes.strip()))
    return go("/review")

@app.post("/school/classes/{class_id}/question")
def school_class_question(class_id: int, question: str = Form(""), resolved: str = Form("")):
    question=question.strip()
    if len(question)>300:
        raise HTTPException(422,"Question must be at most 300 characters")
    with db() as conn:
        require_class(conn,class_id)
        conn.execute("""INSERT INTO class_questions(class_id,day,question,resolved)
            VALUES(?,?,?,?) ON CONFLICT(class_id,day) DO UPDATE SET
            question=excluded.question,resolved=excluded.resolved,updated_at=CURRENT_TIMESTAMP""",
            (class_id,today(),question,int(resolved=="yes")))
    return go("/review")

@app.post("/classes/{class_id}/entries")
def add_entry(class_id: int, kind: str = Form(...), details: str = Form(...), submission_token: str = Form("")):
    try:
        task = validate_task(TaskInput(class_id=class_id, kind=kind, details=details))
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    if submission_token and (len(submission_token) != 64 or any(c not in "0123456789abcdef" for c in submission_token)):
        raise HTTPException(422, "Invalid submission token")
    with db() as conn:
        require_class(conn, task.class_id)
        try:
            conn.execute("INSERT INTO entries(class_id, kind, details, submission_token) VALUES (?, ?, ?, ?)",
                         (task.class_id, task.kind, task.details, submission_token or None))
        except sqlite3.IntegrityError as error:
            if submission_token and "submission_token" in str(error):
                return go()  # Retry of the same form; do not insert another task.
            raise
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

@app.post("/parent/entries/{entry_id}/canvas-link")
def link_canvas_task(entry_id: int, canvas_assignment_id: int = Form(...)):
    """Associate a manual task with an imported Canvas assignment, without merging data."""
    with db() as conn:
        entry = conn.execute("SELECT class_id FROM entries WHERE id=?", (entry_id,)).fetchone()
        if entry is None:
            raise HTTPException(404, "Task not found")
        assignment = conn.execute("""SELECT 1 FROM canvas_assignments a
            JOIN canvas_course_links l ON l.canvas_course_id=a.canvas_course_id
            WHERE a.id=? AND l.class_id=?""", (canvas_assignment_id, entry['class_id'])).fetchone()
        if assignment is None:
            raise HTTPException(422, "Choose a Canvas assignment from the same class")
        conn.execute("""INSERT INTO entry_canvas_links(entry_id,canvas_assignment_id)
            VALUES (?,?) ON CONFLICT(entry_id) DO UPDATE SET
            canvas_assignment_id=excluded.canvas_assignment_id""", (entry_id, canvas_assignment_id))
    return go('/parent')


@app.post("/parent/entries/{entry_id}/canvas-unlink")
def unlink_canvas_task(entry_id: int):
    with db() as conn:
        if not conn.execute("SELECT 1 FROM entries WHERE id=?", (entry_id,)).fetchone():
            raise HTTPException(404, "Task not found")
        conn.execute("DELETE FROM entry_canvas_links WHERE entry_id=?", (entry_id,))
    return go('/parent')


@app.post("/entries/{entry_id}/edit")
def edit_entry(entry_id: int, kind: str = Form(...), details: str = Form(...)):
    try:
        kind, details = validate_task_details(kind, details)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    with db() as conn:
        result = conn.execute("""UPDATE entries SET kind=?, details=?
            WHERE id=? AND kind != 'Nothing Tonight'""", (kind, details, entry_id))
        if not result.rowcount:
            raise HTTPException(404, "Entry not found")
    return go("/parent")

@app.post("/settings/expectations/add")
def add_expectation(class_id: int = Form(...), kind: str = Form("Study"),
                    details: str = Form(...), frequency: str = Form("daily")):
    if frequency not in ("daily", "weekdays"):
        raise HTTPException(422, "Choose daily or weekdays")
    try:
        task = validate_task(TaskInput(class_id=class_id, kind=kind, details=details))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    with db() as conn:
        require_class(conn, task.class_id)
        conn.execute("""INSERT INTO recurring_expectations(class_id,kind,details,frequency)
            VALUES (?,?,?,?)""", (task.class_id,task.kind,task.details,frequency))
    return go("/settings")


@app.post("/settings/expectations/{expectation_id}/toggle")
def toggle_expectation(expectation_id: int):
    with db() as conn:
        result = conn.execute("""UPDATE recurring_expectations
            SET enabled=1-enabled WHERE id=?""", (expectation_id,))
        if not result.rowcount:
            raise HTTPException(404, "Expectation not found")
    return go("/settings")


@app.post("/parent/tasks/add")
def parent_add_task(class_id: int = Form(...), kind: str = Form(...),
                    details: str = Form(...), planned_date: str = Form("")):
    from datetime import date
    try:
        task = validate_task(TaskInput(class_id=class_id, kind=kind, details=details))
        planned = date.fromisoformat(planned_date).isoformat() if planned_date else None
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    with db() as conn:
        require_class(conn, task.class_id)
        conn.execute("""INSERT INTO entries(class_id,kind,details,origin,planned_date)
                        VALUES (?,?,?,'parent',?)""",
                     (task.class_id,task.kind,task.details,planned))
    return go("/parent")


@app.post("/parent/entries/{entry_id}/plan")
def parent_plan_task(entry_id: int, planned_date: str = Form("")):
    from datetime import date
    try:
        planned = date.fromisoformat(planned_date).isoformat() if planned_date else None
    except ValueError as exc:
        raise HTTPException(422, "Invalid work date") from exc
    with db() as conn:
        result=conn.execute("UPDATE entries SET planned_date=? WHERE id=?", (planned,entry_id))
        if not result.rowcount:
            raise HTTPException(404,"Entry not found")
    return go("/parent")


@app.post("/parent/entries/{entry_id}/delete")
def delete_entry(entry_id: int):
    """Only manual tasks live in entries; imported Canvas assignments are separate."""
    with db() as conn:
        result = conn.execute("DELETE FROM entries WHERE id=? AND kind != 'Nothing Tonight'", (entry_id,))
        if not result.rowcount:
            raise HTTPException(404, "Entry not found")
    return go("/parent")

@app.post("/entries/{entry_id}/toggle")
def toggle_entry(entry_id: int):
    """Legacy endpoint retained for existing tests; UI only exposes Done in Homework Review."""
    with db() as conn:
        result = conn.execute("""UPDATE entries SET done=1-done, progress=CASE WHEN done=0 THEN 'done' ELSE 'not_started' END, completed_at=CASE WHEN done=0 THEN CURRENT_TIMESTAMP ELSE NULL END, parent_confirmed=0
            WHERE id=? AND kind != 'Nothing Tonight'""", (entry_id,))
        if not result.rowcount:
            raise HTTPException(404, "Entry not found")
    return go()

@app.post("/entries/{entry_id}/progress")
def update_entry_progress(entry_id: int, progress: str = Form(...)):
    if progress not in ("not_started", "in_progress", "done"):
        raise HTTPException(422, "Invalid task progress")
    with db() as conn:
        result = conn.execute(
            """UPDATE entries SET progress=?, done=?, parent_confirmed=CASE
            WHEN ?='done' THEN parent_confirmed ELSE 0 END, completed_at=CASE WHEN ?='done' THEN COALESCE(completed_at,CURRENT_TIMESTAMP) ELSE NULL END
            WHERE id=? AND kind != 'Nothing Tonight'""",
            (progress, int(progress == "done"), progress, progress, entry_id),
        )
        if not result.rowcount:
            raise HTTPException(404, "Entry not found")
    return go("/home")


@app.post("/entries/{entry_id}/done")
def mark_entry_done(entry_id: int):
    """Idempotent completion action for Homework Review."""
    with db() as conn:
        result = conn.execute("""UPDATE entries SET done=1, progress='done', completed_at=CURRENT_TIMESTAMP, parent_confirmed=0
            WHERE id=? AND done=0 AND kind != 'Nothing Tonight'""", (entry_id,))
        if not result.rowcount:
            raise HTTPException(409, "Task not found or already done")
    return go("/home")

@app.post("/parent/entries/{entry_id}/confirm")
def parent_confirm(entry_id: int):
    try:
        confirm_task(entry_id)
    except ParentReviewError as error:
        raise HTTPException(error.status_code, error.message) from error
    return go("/parent")

@app.post("/parent/entries/{entry_id}/return")
def parent_return(entry_id: int):
    try:
        return_task(entry_id)
    except ParentReviewError as error:
        raise HTTPException(error.status_code, error.message) from error
    return go("/parent")

@app.post("/parent/entries/{entry_id}/note")
def parent_note(entry_id: int, note: str = Form("")):
    try:
        save_coaching_note(entry_id, note)
    except ParentReviewError as error:
        raise HTTPException(error.status_code, error.message) from error
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
from synccanvas.lunch_buddies import router as lunch_buddies_router
app.include_router(parent_schedule_router)
app.include_router(lunch_buddies_router)
from synccanvas.school_days import router as school_days_router
app.include_router(school_days_router)
