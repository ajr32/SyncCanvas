
"""Parent class administration for the local SyncCanvas prototype."""

from __future__ import annotations

import logging
import sqlite3

from fastapi import APIRouter, Form
from fastapi.responses import HTMLResponse, RedirectResponse

from synccanvas.canvas_settings import get_canvas_settings
from synccanvas.database import db
from synccanvas.pages import esc, layout
from synccanvas.services.canvas_http import CanvasHTTP
from synccanvas.services.canvas_reader import CanvasReadError
from synccanvas.services.canvas_course_discovery import discover_from_http
from synccanvas.services.class_management import (
    ClassManagementError,
    add_class,
    delete_empty_class,
    list_classes,
    rename_class,
    set_archived,
    set_enabled,
)

router = APIRouter(prefix="/parent/classes")
logger = logging.getLogger(__name__)


def back():
    return RedirectResponse("/parent/classes", status_code=303)


def error_response(message: str, status_code: int = 400):
    page = layout(
        "Class management error",
        '<section class="panel">'
        f'<p>{esc(message)}</p>'
        '<p><a href="/parent/classes">Back to Manage Classes</a></p>'
        '</section>',
    )
    page.status_code = status_code
    return page


def course_search():
    url, token = get_canvas_settings()

    if not url or not token:
        raise ValueError(
            "Canvas is not configured. Check the Canvas URL and token "
            "in the project .env file."
        )

    client = CanvasHTTP(base_url=url, token=token)
    return discover_from_http(client)


def class_options(classes):
    choices = ['<option value="0">Create a new class</option>']
    for cls in classes:
        choices.append(
            f'<option value="{cls.id}">{esc(cls.name)}</option>'
        )
    return "".join(choices)


@router.get("", response_class=HTMLResponse)
def manage_classes():
    return render_page()


@router.post("/search", response_class=HTMLResponse)
def search_canvas():
    try:
        discovered = course_search()

    except CanvasReadError as error:
        return render_page(
            message=f"Canvas course search failed: {error}"
        )

    except ValueError:
        return render_page(
            message=(
                "Canvas course search could not start. "
                "Check the Canvas URL and token in the "
                "project .env file."
            )
        )

    except Exception:
        logger.error(
            "Unexpected Canvas course discovery failure",
            exc_info=False,
        )
        return render_page(
            message=(
                "Canvas course discovery encountered an unexpected "
                "error. The Canvas connection may be working, "
                "but the returned courses could not be processed."
            )
        )

    return render_page(discovered=discovered)


def render_page(discovered=None, message=""):
    with db() as conn:
        classes = list_classes(conn)

    parts = [
        '<section class="panel">',
        '<p><a href="/parent">← Parent dashboard</a></p>',
        '<h3>Canvas course discovery</h3>',
        '<p>Searching does not add, link, or import any courses.</p>',
        '<form method="post" action="/parent/classes/search">',
        '<button type="submit">Search Canvas for Classes</button>',
        '</form>',
        '</section>',
    ]

    if message:
        parts.append(
            '<section class="panel">'
            f'<p>{esc(message)}</p>'
            '</section>'
        )

    if discovered is not None:
        linked_ids = {
            cls.canvas_course_id
            for cls in classes
            if cls.canvas_course_id is not None
        }

        parts.append(
            '<section class="panel">'
            f'<h3>Canvas courses found: {len(discovered)}</h3>'
        )

        if not discovered:
            parts.append('<p>No courses were returned.</p>')

        for course in discovered:
            linked = course.canvas_course_id in linked_ids
            parts.append(
                '<div class="class">'
                f'<strong>{esc(course.name)}</strong>'
                f' <small>(Canvas #{course.canvas_course_id})</small>'
            )

            if course.course_code:
                parts.append(
                    f'<p><small>{esc(course.course_code)}</small></p>'
                )

            if linked:
                parts.append('<p>Already linked</p>')
            else:
                parts.append(
                    '<form method="post" '
                    'action="/parent/classes/link">'
                    f'<input type="hidden" name="canvas_course_id" '
                    f'value="{course.canvas_course_id}">'
                    f'<input type="hidden" name="course_name" '
                    f'value="{esc(course.name)}">'
                    '<label>Link this Canvas course to:</label>'
                    '<select name="class_id">'
                    f'{class_options(classes)}'
                    '</select> '
                    '<button type="submit">Link course</button>'
                    '</form>'
                )

            parts.append('</div>')

        parts.append('</section>')

    parts.append(
        '<section class="panel">'
        '<h3>Add a manual class</h3>'
        '<form method="post" action="/parent/classes/add">'
        '<label>Class name</label>'
        '<input type="text" name="name" maxlength="80" required>'
        ' <button type="submit">Add class</button>'
        '</form>'
        '</section>'
    )

    parts.append(
        '<section class="panel">'
        '<h3>Manage existing classes</h3>'
        '<p>Disabled and archived classes remain saved. '
        'Only enabled, non-archived classes should appear '
        'in the student planner.</p>'
    )

    if not classes:
        parts.append('<p>No classes yet.</p>')

    for cls in classes:
        status = (
            "Archived" if cls.archived
            else "Enabled" if cls.enabled
            else "Disabled"
        )
        link = (
            f"Canvas #{cls.canvas_course_id}"
            if cls.canvas_course_id is not None
            else "Manual / unlinked"
        )

        parts.extend([
            '<div class="class">',
            f'<h4>{esc(cls.name)}</h4>',
            f'<p><small>{esc(status)} · {esc(link)}</small></p>',
            '<form method="post" '
            f'action="/parent/classes/{cls.id}/rename">',
            '<label>Rename</label>',
            f'<input name="name" value="{esc(cls.name)}" '
            'maxlength="80" required>',
            ' <button type="submit">Rename</button>',
            '</form>',
            '<div class="row">',
            '<form method="post" '
            f'action="/parent/classes/{cls.id}/enabled">',
            f'<input type="hidden" name="enabled" '
            f'value="{0 if cls.enabled else 1}">',
            '<button class="secondary" type="submit">',
            'Disable' if cls.enabled else 'Enable',
            '</button></form>',
            '<form method="post" '
            f'action="/parent/classes/{cls.id}/archived">',
            f'<input type="hidden" name="archived" '
            f'value="{0 if cls.archived else 1}">',
            '<button class="secondary" type="submit">',
            'Restore' if cls.archived else 'Archive',
            '</button></form>',
            '</div>',
            '<form method="post" '
            f'action="/parent/classes/{cls.id}/delete" '
            'onsubmit="return confirm('
            "'Delete this class only if it has no history?');"
            '">',
            '<button class="secondary" type="submit">'
            'Delete empty class</button>',
            '</form>',
            '</div>',
        ])

    parts.append('</section>')

    return layout("Manage Classes", "".join(parts))


@router.post("/add")
def add_manual_class(name: str = Form(...)):
    try:
        with db() as conn:
            add_class(conn, name)
    except ClassManagementError as error:
        return error_response(str(error))
    return back()


@router.post("/{class_id}/rename")
def rename(class_id: int, name: str = Form(...)):
    try:
        with db() as conn:
            rename_class(conn, class_id, name)
    except ClassManagementError as error:
        return error_response(str(error))
    return back()


@router.post("/{class_id}/enabled")
def change_enabled(class_id: int, enabled: int = Form(...)):
    if enabled not in (0, 1):
        return error_response("Invalid enabled value.")

    try:
        with db() as conn:
            set_enabled(conn, class_id, bool(enabled))
    except ClassManagementError as error:
        return error_response(str(error))
    return back()


@router.post("/{class_id}/archived")
def change_archived(class_id: int, archived: int = Form(...)):
    if archived not in (0, 1):
        return error_response("Invalid archived value.")

    try:
        with db() as conn:
            set_archived(conn, class_id, bool(archived))
    except ClassManagementError as error:
        return error_response(str(error))
    return back()


@router.post("/{class_id}/delete")
def delete(class_id: int):
    try:
        with db() as conn:
            delete_empty_class(conn, class_id)
    except ClassManagementError as error:
        return error_response(str(error))
    return back()


@router.post("/link")
def link_canvas_course(
    canvas_course_id: int = Form(...),
    class_id: int = Form(...),
    course_name: str = Form(...),
):
    if canvas_course_id <= 0 or class_id < 0:
        return error_response("Invalid course selection.")

    try:
        with db() as conn:
            existing = conn.execute(
                """
                SELECT class_id
                FROM canvas_course_links
                WHERE canvas_course_id=?
                """,
                (canvas_course_id,),
            ).fetchone()

            if existing is not None:
                raise ClassManagementError(
                    "This Canvas course is already linked."
                )

            if class_id == 0:
                class_id = add_class(conn, course_name)
            else:
                row = conn.execute(
                    "SELECT id FROM classes WHERE id=?",
                    (class_id,),
                ).fetchone()

                if row is None:
                    raise ClassManagementError(
                        "The selected planner class does not exist."
                    )

            already_linked = conn.execute(
                """
                SELECT canvas_course_id
                FROM canvas_course_links
                WHERE class_id=?
                """,
                (class_id,),
            ).fetchone()

            if already_linked is not None:
                raise ClassManagementError(
                    "This planner class already has a Canvas link. "
                    "Relinking needs a separate review."
                )

            conn.execute(
                """
                INSERT INTO canvas_course_links(
                    canvas_course_id, class_id
                )
                VALUES (?, ?)
                """,
                (canvas_course_id, class_id),
            )

    except (ClassManagementError, sqlite3.IntegrityError) as error:
        return error_response(
            str(error)
            if isinstance(error, ClassManagementError)
            else "The Canvas link conflicts with an existing link."
        )

    return back()
