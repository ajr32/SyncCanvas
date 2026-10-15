
"""HTML pages and presentation helpers for the local SyncCanvas prototype."""

import html
import json
from datetime import date, timedelta

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from synccanvas.database import db
from synccanvas.services.tasks import ALLOWED_KINDS
from synccanvas.services.sync_coordinator import sync_coordinator
from synccanvas.services.sync_status import present_sync_status
from synccanvas.models.sync_result import SyncState

router = APIRouter()
KINDS = ALLOWED_KINDS

ACTIVE_CLASSES = """
    SELECT id, name
    FROM classes
    WHERE enabled=1 AND archived=0
    ORDER BY sort_order, id
"""


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def layout(title: str, content: str) -> HTMLResponse:
    css = """
    body {
        font-family: system-ui, Arial, sans-serif;
        background: #f4f7fb;
        color: #18253b;
        margin: 0;
    }
    header {
        background: #193a63;
        color: white;
        padding: 18px max(20px, calc((100vw - 940px)/2));
    }
    header nav { display: flex; flex-wrap: wrap; align-items: center; gap: 10px 20px; }
    header a {
        color: white;
        margin-right: 0;
    }
    header a.parent-link { margin-left: auto; }
    main {
        max-width: 940px;
        margin: 28px auto;
        padding: 0 18px;
    }
    .panel {
        background: white;
        border: 1px solid #dce4ee;
        border-radius: 12px;
        padding: 20px;
        margin: 16px 0;
    }
    .class {
        border-top: 1px solid #e1e8f0;
        padding: 14px 0;
    }
    .canvas-card {
        border: 1px solid #dce4ee;
        border-radius: 10px;
        padding: 12px 14px;
        margin: 10px 0;
        background: #fff;
    }
    .canvas-meta {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 8px 12px;
        margin-top: 6px;
        line-height: 1.5;
    }
    .canvas-open {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        box-sizing: border-box;
        min-height: 44px;
        padding: 8px 13px;
        border-radius: 8px;
        background: #1659a2;
        color: white;
        font-size: 0.9rem;
        font-weight: 600;
        text-decoration: none;
        white-space: nowrap;
    }
    .canvas-open:hover, .canvas-open:focus-visible { background: #103e75; color: white; }
    .canvas-open:focus-visible { outline: 3px solid #ffbf47; outline-offset: 3px; }
    input, select, button {
        font: inherit;
        padding: 10px;
        border-radius: 7px;
        border: 1px solid #9baec4;
    }
    button {
        background: #1659a2;
        color: white;
        border: 0;
        cursor: pointer;
    }
    button.secondary {
        background: #e5edf7;
        color: #193a63;
    }
    label {
        display: block;
        margin: 8px 0 4px;
    }
    form.inline {
        display: inline;
    }
    small {
        color: #52647b;
    }
    .done {
        text-decoration: line-through;
        color: #64748b;
    }
    .row {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 10px;
    }
    a {
        color: #1659a2;
    }
    .status {
        font-weight: 600;
    }
    .unchecked {
        color: #a34d00;
    }
    .checked {
        color: #147044;
    }
    input[type=text] {
        min-width: 220px;
    }
    @media(max-width:580px) {
        input, select, button { max-width: 100%; }
        .row > * { flex: 1 1 170px; }
    }
    """

    return HTMLResponse(
        f'<!doctype html>'
        f'<html lang="en">'
        f'<head>'
        f'<meta charset="utf-8">'
        f'<meta name="viewport" '
        f'content="width=device-width,initial-scale=1">'
        f'<title>{esc(title)} · SyncCanvas</title>'
        f'<style>{css}</style>'
        f'</head>'
        f'<body>'
        f'<header>'
        f'<h1>SyncCanvas</h1>'
        f'<nav>'
        f'<a href="/">My Classes</a>'
        f'<a href="/review">Course Check-Out</a>'
        f'<a href="/home">Homework Review</a>'
        f'<a class="parent-link" href="/parent">Parent Page</a>'
        f'</nav>'
        f'</header>'
        f'<main>'
        f'<h2>{esc(title)}</h2>'
        f'{content}'
        f'<p><small>'
        f'Local prototype only · No accounts or cloud sync yet · '
        f'Do not publish online'
        f'</small></p>'
        f'</main>'
        f'</body>'
        f'</html>'
    )


def today() -> str:
    return date.today().isoformat()


def options(selected: str = "") -> str:
    return "".join(
        f'<option value="{esc(kind)}"'
        f'{" selected" if kind == selected else ""}>'
        f'{esc(kind)}</option>'
        for kind in KINDS
    )


def get_active_classes(conn):
    return conn.execute(ACTIVE_CLASSES).fetchall()


def get_canvas_assignments(conn):
    """Return assignments for active, linked classes only."""
    return conn.execute(
        """
        SELECT a.id, a.title, a.due_date, a.due_at,
               a.html_url, a.submission_types, a.completed, c.id AS class_id,
               c.name AS class_name, c.sort_order
        FROM canvas_assignments a
        JOIN canvas_course_links l
          ON l.canvas_course_id = a.canvas_course_id
        JOIN classes c ON c.id = l.class_id
        WHERE c.enabled = 1 AND c.archived = 0
        ORDER BY
            CASE WHEN a.due_date IS NULL OR a.due_date = ''
                 THEN 1 ELSE 0 END,
            a.due_date, a.due_at, a.title, a.id
        """
    ).fetchall()


def canvas_due_label(assignment):
    due = assignment["due_date"]
    if not due:
        return "No due date"
    if due < today():
        return f"Overdue · {due}"
    if due == today():
        return "Due today"
    return f"Due {due}"


def submission_label(raw):
    labels = {
        "on_paper": "Turn in on paper",
        "online_upload": "Upload a file",
        "online_text_entry": "Type an answer online",
        "online_url": "Submit a website link",
        "online_quiz": "Online quiz",
        "external_tool": "External tool",
        "discussion_topic": "Discussion",
        "none": "No submission required",
        "not_graded": "Not graded",
        "media_recording": "Record audio or video",
        "student_annotation": "Annotate a document",
    }
    try:
        values = json.loads(raw or "[]")
    except (ValueError, TypeError):
        return "Submission method unavailable"
    if not isinstance(values, list) or not values:
        return "Submission method not specified"
    return " / ".join(labels.get(x, x.replace("_", " ").capitalize()) for x in values if isinstance(x, str))


def canvas_assignment_html(assignment, *, show_class=False):
    """Canvas is read-only: no local completion toggle on imported work."""
    title = esc(assignment["title"])
    url = str(assignment["html_url"] or "").strip()
    # Only allow HTTPS links; never inject arbitrary Canvas-provided URLs.
    link = (
        f'<a class="canvas-open" href="{esc(url)}" target="_blank" rel="noopener noreferrer">'
        'Open in Canvas ↗</a>'
        if url.lower().startswith("https://")
        else ""
    )
    class_prefix = (
        f'<strong>{esc(assignment["class_name"])}</strong>: '
        if show_class else ""
    )
    status = "Completed" if assignment["completed"] else canvas_due_label(assignment)
    return (
        '<div class="canvas-card">'
        f'<strong>{class_prefix}{title}</strong>'
        f'<div class="canvas-meta"><small>{esc(status)} · {esc(submission_label(assignment["submission_types"]))}</small>{link}</div>'
        '</div>'
    )


def completed_canvas_history(assignments):
    """Seven-day history based on due date, not completion timestamp."""
    cutoff = (date.today() - timedelta(days=7)).isoformat()
    return [
        a for a in assignments
        if a["completed"] and a["due_date"] and a["due_date"] >= cutoff
    ]


def canvas_history_html(assignments):
    recent = completed_canvas_history(assignments)
    parts = [
        '<details class="panel">',
        f'<summary>Recently completed Canvas assignments ({len(recent)})</summary>',
        '<p><small>Last 7 days by assignment due date; '
        'completion dates are not available yet.</small></p>',
    ]
    if not recent:
        parts.append('<p>No completed Canvas assignments due in the last 7 days.</p>')
    else:
        for assignment in reversed(recent):
            parts.append(canvas_assignment_html(assignment, show_class=True))
    parts.append('</details>')
    return "".join(parts)


@router.get("/", response_class=HTMLResponse)
def student():
    with db() as conn:
        classes = get_active_classes(conn)
        canvas_assignments = get_canvas_assignments(conn)

        entries = conn.execute(
            """
            SELECT
                e.id, e.class_id, e.kind, e.details,
                e.done, e.parent_confirmed, e.coaching_note
            FROM entries e
            JOIN classes c ON c.id=e.class_id
            WHERE e.kind != 'Nothing Tonight'
              AND c.enabled=1 AND c.archived=0
            ORDER BY e.id DESC
            """
        ).fetchall()

        checkins = {
            row["class_id"]: row["nothing_tonight"]
            for row in conn.execute(
                """
                SELECT ch.class_id, ch.nothing_tonight
                FROM checkins ch
                JOIN classes c ON c.id=ch.class_id
                WHERE ch.day=?
                  AND c.enabled=1 AND c.archived=0
                """,
                (today(),),
            )
        }

    canvas_by_class = {}
    for assignment in canvas_assignments:
        if not assignment["completed"]:
            canvas_by_class.setdefault(assignment["class_id"], []).append(assignment)

    by_class = {}
    for entry in entries:
        by_class.setdefault(entry["class_id"], []).append(entry)

    sync = present_sync_status(sync_coordinator.status())

    parts = [
        '<section class="panel">'
        '<h3>School updates</h3>'
        f'<p><strong>{esc(sync.label)}</strong> — '
        f'{esc(sync.message)}</p>'
        + (
            '<form method="post" action="/sync/run">'
            '<button type="submit">Check for updates</button>'
            '</form>'
            if sync.state not in (
                SyncState.NOT_CONFIGURED.value,
                SyncState.RUNNING.value,
            ) else ''
        )
        + '</section>'
    ]

    # Poll only while a synchronization is running. A completed sync
    # reloads the page so fresh assignments and the status appear together.
    if sync.state == SyncState.RUNNING.value:
        parts.append("""
            <script>
            (function () {
                let failures = 0;
                async function checkSync() {
                    try {
                        const response = await fetch('/api/sync/status', {
                            cache: 'no-store',
                            headers: { 'Accept': 'application/json' }
                        });
                        if (!response.ok) throw new Error('Status unavailable');
                        const status = await response.json();
                        failures = 0;
                        if (status.state !== 'running') {
                            window.location.reload();
                            return;
                        }
                    } catch (error) {
                        failures += 1;
                        if (failures >= 5) {
                            window.location.reload();
                            return;
                        }
                    }
                    window.setTimeout(checkSync, 1500);
                }
                window.setTimeout(checkSync, 1500);
            }());
            </script>
        """)

    if not classes:
        parts.append(
            '<section class="panel">'
            '<p>No active classes are available yet. '
            'Classes are managed from the Parent page.</p>'
            '</section>'
        )

    for cls in classes:
        cid = cls["id"]

        if cid not in checkins:
            state = "Not checked yet"
        elif checkins[cid]:
            state = "Nothing tonight"
        else:
            state = "Checked today"

        css_class = (
            "unchecked" if cid not in checkins else "checked"
        )

        parts.append(
            f'<section class="panel">'
            f'<h3>{esc(cls["name"])}</h3>'
            f'<p class="status {css_class}">{state}</p>'
        )

        canvas_items = canvas_by_class.get(cid, [])
        if canvas_items:
            parts.append('<h4>Canvas assignments to do</h4>')
            for assignment in canvas_items:
                parts.append(canvas_assignment_html(assignment))

        for item in by_class.get(cid, []):
            status = ' class="done"' if item["done"] else ""
            detail = (
                f' — {esc(item["details"])}'
                if item["details"] else ""
            )

            if item["parent_confirmed"]:
                confirmation = " · Parent confirmed"
            elif item["done"]:
                confirmation = " · Waiting for parent review"
            else:
                confirmation = ""

            note = (
                f'<p><small>Parent note: '
                f'{esc(item["coaching_note"])}</small></p>'
                if item["coaching_note"] else ""
            )

            button_label = "Undo" if item["done"] else "Done"

            parts.append(
                f'<div class="class">'
                f'<span{status}>'
                f'<strong>{esc(item["kind"])}</strong>'
                f'{detail}'
                f'</span>'
                f'{esc(confirmation)} '
                f'{note}'
                f'<form class="inline" method="post" '
                f'action="/entries/{item["id"]}/toggle">'
                f'<button type="submit">{button_label}</button>'
                f'</form> '
                f'<a href="/entries/{item["id"]}/edit">'
                f'Edit</a>'
                f'</div>'
            )

        parts.append(
            f'<form method="post" '
            f'action="/classes/{cid}/entries">'
            f'<label for="kind-{cid}">'
            f'What needs to happen?</label>'
            f'<select id="kind-{cid}" name="kind">'
            f'{options()}'
            f'</select>'
            f'<label for="details-{cid}">'
            f'What exactly? (required)</label>'
            f'<input type="text" id="details-{cid}" '
            f'name="details" required maxlength="300" '
            f'placeholder="e.g. Questions 1–10">'
            f'<button type="submit">'
            f'Add task & check in</button>'
            f'</form>'
        )

        parts.append(
            f'<div class="row">'
            f'<form class="inline" method="post" '
            f'action="/classes/{cid}/nothing">'
            f'<button class="secondary" type="submit">'
            f'Nothing Tonight</button>'
            f'</form> '
            f'<form class="inline" method="post" '
            f'action="/classes/{cid}/checkin">'
            f'<button class="secondary" type="submit">'
            f'Checked — still deciding</button>'
            f'</form>'
            f'</div>'
            f'</section>'
        )

    parts.append(canvas_history_html(canvas_assignments))
    return layout("My Classes", "".join(parts))


@router.get("/review", response_class=HTMLResponse)
def review():
    with db() as conn:
        classes = get_active_classes(conn)

        checked = {
            row["class_id"]: row["nothing_tonight"]
            for row in conn.execute(
                """
                SELECT ch.class_id, ch.nothing_tonight
                FROM checkins ch
                JOIN classes c ON c.id=ch.class_id
                WHERE ch.day=?
                  AND c.enabled=1 AND c.archived=0
                """,
                (today(),),
            )
        }

    parts = [
        '<section class="panel">'
        f'<p>Before leaving school, check every class '
        f'for today ({esc(today())}). '
        f'Make sure you have what you need '
        f'to bring home.</p>'
    ]

    for cls in classes:
        if cls["id"] not in checked:
            state = "Not checked yet"
        elif checked[cls["id"]]:
            state = "Nothing tonight"
        else:
            state = "Checked today"

        parts.append(
            f'<div class="class">'
            f'<strong>{esc(cls["name"])}</strong>'
            f' — {esc(state)} '
            f'<a href="/">Open class</a>'
            f'</div>'
        )

    parts.append("</section>")
    return layout("Course Check-Out", "".join(parts))


@router.get("/home", response_class=HTMLResponse)
def home():
    with db() as conn:
        canvas_assignments = get_canvas_assignments(conn)
        entries = conn.execute(
            """
            SELECT
                c.name,
                e.id,
                e.kind,
                e.details,
                e.done
            FROM entries e
            JOIN classes c ON c.id=e.class_id
            WHERE e.kind != 'Nothing Tonight'
              AND e.done=0
              AND c.enabled=1 AND c.archived=0
            ORDER BY c.sort_order, c.id, e.id
            """
        ).fetchall()

    parts = [
        '<section class="panel">'
        '<h3>Canvas assignments to do</h3>'
        '<p>All incomplete assignments, including overdue work, '
        'sorted by due date.</p>'
    ]
    incomplete = [a for a in canvas_assignments if not a["completed"]]
    if not incomplete:
        parts.append('<p>No incomplete Canvas assignments.</p>')
    for assignment in incomplete:
        parts.append(canvas_assignment_html(assignment, show_class=True))
    parts.append('</section>')
    parts.append(canvas_history_html(canvas_assignments))

    parts.extend([
        '<section class="panel">'
        '<h3>My added tasks</h3>'
        '<p>Tasks still open, including tasks '
        'from previous days.</p>'
    ])

    if not entries:
        parts.append("<p>No open tasks recorded.</p>")

    for item in entries:
        parts.append(
            f'<div class="class">'
            f'<strong>{esc(item["name"])}</strong>: '
            f'{esc(item["kind"])} — '
            f'{esc(item["details"])} '
            f'<form class="inline" method="post" '
            f'action="/entries/{item["id"]}/toggle">'
            f'<button>Done</button>'
            f'</form>'
            f'</div>'
        )

    parts.append("</section>")
    return layout("Homework Review", "".join(parts))


@router.get("/parent", response_class=HTMLResponse)
def parent():
    with db() as conn:
        classes = get_active_classes(conn)

        checkins = {
            row["class_id"]: row["nothing_tonight"]
            for row in conn.execute(
                """
                SELECT ch.class_id, ch.nothing_tonight
                FROM checkins ch
                JOIN classes c ON c.id=ch.class_id
                WHERE ch.day=?
                  AND c.enabled=1 AND c.archived=0
                """,
                (today(),),
            )
        }

        tasks = conn.execute(
            """
            SELECT
                e.id,
                e.class_id,
                e.kind,
                e.details,
                e.done,
                e.parent_confirmed,
                e.coaching_note
            FROM entries e
            JOIN classes c ON c.id=e.class_id
            WHERE e.kind != 'Nothing Tonight'
              AND c.enabled=1 AND c.archived=0
            ORDER BY e.id DESC
            """
        ).fetchall()

    tasks_by_class = {}
    for task in tasks:
        tasks_by_class.setdefault(
            task["class_id"], []
        ).append(task)

    checked_count = sum(
        c["id"] in checkins for c in classes
    )
    open_count = sum(
        not t["done"] for t in tasks
    )
    awaiting_count = sum(
        t["done"] and not t["parent_confirmed"]
        for t in tasks
    )

    missing = [
        c for c in classes
        if c["id"] not in checkins
    ]

    ask_teacher = [
        t for t in tasks
        if t["kind"] == "Ask Teacher"
        and not t["done"]
    ]

    parts = [
        '<section class="panel">'
        '<h3>Class administration</h3>'
        '<p>Search Canvas, link courses, and manage '
        'enabled, disabled, or archived classes.</p>'
        '<p><a href="/parent/classes">Manage Classes</a></p>'
        '</section>',
        '<section class="panel">'
        '<h3>Afternoon review</h3>',
        f'<p><strong>{checked_count}/{len(classes)}</strong> '
        f'classes checked today · '
        f'<strong>{open_count}</strong> unfinished tasks · '
        f'<strong>{awaiting_count}</strong> '
        f'awaiting parent confirmation · '
        f'<strong>{len(missing) + len(ask_teacher)}</strong> '
        f'attention items</p>',
        '<p><small>Class check-ins apply to today; '
        'unfinished tasks can be from earlier days. '
        'Archived and disabled classes are excluded '
        'from the daily review.</small></p></section>',
    ]

    if not classes:
        parts.append(
            '<section class="panel">'
            '<p>No active classes yet. '
            '<a href="/parent/classes">Manage Classes</a> '
            'to add or enable classes.</p>'
            '</section>'
        )
    else:
        ordered = missing + [
            c for c in classes
            if c["id"] in checkins
        ]

        parts.append(
            '<section class="panel">'
            '<h3>All classes</h3>'
        )

        for cls in ordered:
            cid = cls["id"]

            if cid not in checkins:
                state = "Not checked yet"
            elif checkins[cid]:
                state = "Nothing tonight"
            else:
                state = "Checked today"

            status_class = (
                "unchecked"
                if cid not in checkins
                else "checked"
            )

            parts.append(
                f'<div class="class">'
                f'<strong>{esc(cls["name"])}</strong>'
                f' — <span class="status {status_class}">'
                f'{esc(state)}</span>'
            )

            unfinished = [
                t for t in tasks_by_class.get(cid, [])
                if not t["done"]
            ]

            if unfinished:
                parts.append("<ul>")
                for task in unfinished:
                    parts.append(
                        f'<li>{esc(task["kind"])}'
                        f' — {esc(task["details"])}</li>'
                    )
                parts.append("</ul>")

            elif cid in checkins and checkins[cid]:
                parts.append(
                    '<p><small>No new work reported tonight. '
                    'Older unfinished tasks, if any, '
                    'would appear above.</small></p>'
                )
            else:
                parts.append(
                    '<p><small>No unfinished tasks '
                    'recorded.</small></p>'
                )

            for task in tasks_by_class.get(cid, []):
                if task["done"]:
                    state = (
                        "Parent confirmed"
                        if task["parent_confirmed"]
                        else "Student says done — review needed"
                    )
                    parts.append(
                        f'<p><small>{esc(task["kind"])}'
                        f' — {esc(task["details"])}: '
                        f'{state}</small></p>'
                    )

                if task["done"] and not task["parent_confirmed"]:
                    parts.append(
                        f'<form class="inline" method="post" '
                        f'action="/parent/entries/'
                        f'{task["id"]}/confirm">'
                        f'<button type="submit">'
                        f'Confirm complete</button>'
                        f'</form> '
                    )
                    parts.append(
                        f'<form class="inline" method="post" '
                        f'action="/parent/entries/'
                        f'{task["id"]}/return">'
                        f'<button class="secondary" type="submit">'
                        f'Needs another look</button>'
                        f'</form>'
                    )

                if task["coaching_note"]:
                    parts.append(
                        f'<p><small>Coaching note: '
                        f'{esc(task["coaching_note"])}'
                        f'</small></p>'
                    )

                parts.append(
                    f'<form method="post" '
                    f'action="/parent/entries/'
                    f'{task["id"]}/note">'
                    f'<label for="note-{task["id"]}">'
                    f'Coaching note (optional)</label>'
                    f'<input id="note-{task["id"]}" '
                    f'name="note" maxlength="300" '
                    f'value="{esc(task["coaching_note"])}">'
                    f'<button class="secondary" type="submit">'
                    f'Save note</button>'
                    f'</form>'
                )

            parts.append("</div>")

        parts.append("</section>")

    if ask_teacher:
        parts.append(
            '<section class="panel">'
            '<h3>Questions needing follow-up</h3>'
        )

        for task in ask_teacher:
            cls_name = next(
                (
                    c["name"]
                    for c in classes
                    if c["id"] == task["class_id"]
                ),
                "Unknown class",
            )
            parts.append(
                f'<p><strong>{esc(cls_name)}</strong>: '
                f'{esc(task["details"])}</p>'
            )

        parts.append("</section>")

    return layout(
        "Parent Page",
        "".join(parts),
    )


@router.get(
    "/entries/{entry_id}/edit",
    response_class=HTMLResponse,
)
def edit_page(entry_id: int):
    with db() as conn:
        entry = conn.execute(
            """
            SELECT e.id, e.kind, e.details
            FROM entries e
            JOIN classes c ON c.id=e.class_id
            WHERE e.id=?
              AND e.kind != 'Nothing Tonight'
              AND c.enabled=1 AND c.archived=0
            """,
            (entry_id,),
        ).fetchone()

    if entry is None:
        raise HTTPException(
            404, "Entry not found"
        )

    form = (
        '<section class="panel">'
        f'<form method="post" '
        f'action="/entries/{entry_id}/edit">'
        '<label>Task type</label>'
        f'<select name="kind">'
        f'{options(entry["kind"])}'
        '</select>'
        '<label>Details</label>'
        '<input type="text" name="details" '
        'required maxlength="300" '
        f'value="{esc(entry["details"])}">'
        '<button>Save changes</button> '
        '<a href="/">Cancel</a>'
        '</form>'
        '</section>'
    )

    return layout("Edit task", form)
