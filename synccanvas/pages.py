
"""Local HTML pages for the SyncCanvas family planner."""
import html
import json
import secrets
import sqlite3
from datetime import date, datetime, timedelta
from synccanvas.services.family_time import family_today
from fastapi import APIRouter, HTTPException, Form
from fastapi.responses import HTMLResponse
from synccanvas.database import db
from synccanvas.services.recurring import ensure_today
from synccanvas.services.tasks import ALLOWED_KINDS
from synccanvas.services.sync_coordinator import sync_coordinator
from synccanvas.services.sync_status import present_sync_status
from synccanvas.models.sync_result import SyncState

router = APIRouter()
KINDS = ALLOWED_KINDS
ACTIVE_CLASSES = "SELECT id, name FROM classes WHERE enabled=1 AND archived=0 ORDER BY sort_order, id"

def esc(value):
    return html.escape(str(value), quote=True)


def american_time(value):
    if not value:
        return ""
    return datetime.strptime(str(value), "%H:%M").strftime("%I:%M %p").lstrip("0")

def friendly_date(value):
    """Display stored ISO calendar dates naturally without changing storage or form values."""
    if not value:
        return ""
    try:
        parsed = date.fromisoformat(str(value))
    except (TypeError, ValueError):
        return str(value)
    return f"{parsed.strftime('%B')} {parsed.day}, {parsed.year}"

def layout(title, content):
    css = """
    body{font-family:system-ui,Arial,sans-serif;background:#f4f7fb;color:#18253b;margin:0}
    header{background:#193a63;color:white;padding:18px max(20px,calc((100vw - 940px)/2))}
    header nav{display:flex;flex-wrap:wrap;align-items:center;gap:10px 20px}
    header a{color:white}header a.parent-link{margin-left:auto}
    header nav a{padding:7px 9px;border-radius:7px;text-decoration:none}header nav a:hover,header nav a:focus-visible{background:#345b85;outline:2px solid white;outline-offset:2px}
    main{max-width:940px;margin:28px auto;padding:0 18px;min-width:0}
    .skip-link{position:absolute;left:12px;top:-100px;background:white;color:#193a63;padding:12px;z-index:100}
    .skip-link:focus{top:8px}
    .panel,.task-card,.canvas-card{min-width:0;overflow-wrap:anywhere}
    input,select,textarea{max-width:100%}
    .row>*,.canvas-meta>*{min-width:0}
    @media(max-width:760px){header{padding:14px 18px}header nav{gap:6px 10px}main{margin:16px auto;padding:0 12px}.panel{padding:14px}}
    @media(max-width:420px){header nav a{flex:1 1 auto;justify-content:center}header a.parent-link{margin-left:0}.task-card{padding:12px}input[type=text]{min-width:0;width:100%}}
    @media(min-width:761px) and (max-width:1100px){main{padding:0 24px}}
    .panel{background:white;border:1px solid #dce4ee;border-radius:12px;padding:20px;margin:16px 0}
    .class{border-top:1px solid #e1e8f0;padding:14px 0}
    .task-group{display:grid;gap:12px}.task-card{border:1px solid #dce4ee;border-radius:10px;padding:16px;background:#fff}.task-card h4{margin:0 0 6px}.task-card p{margin:6px 0}.task-top{display:flex;justify-content:space-between;align-items:start;gap:12px;flex-wrap:wrap}.task-source{font-size:.82rem;font-weight:700;color:#52647b}.task-progress{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.task-progress select{min-width:145px}.muted{color:#52647b}.summary-grid{display:flex;gap:12px;flex-wrap:wrap}.summary-grid span{background:#edf3fb;border-radius:8px;padding:10px 14px}.canvas-card{border:1px solid #dce4ee;border-radius:10px;padding:12px 14px;margin:10px 0;background:white}
    .category-tag{display:inline-block;border-radius:6px;background:#eaf1fa;color:#193a63;padding:3px 8px;font-size:.8rem;font-weight:650}.category-form{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin:8px 0}.category-form label{margin:0}.category-form select{min-width:140px}.compact-canvas{padding:10px;border-top:1px solid #e1e8f0}.compact-canvas p{margin:4px 0}.linked-work{border-top:1px solid #dce4ee;margin-top:14px;padding-top:12px}.linked-work h5{font-size:1rem;margin:0 0 6px}.linked-child{background:#f7faff;margin:10px 0 0 16px;border-left:4px solid #7598c7}.linked-child .task-class{font-size:1rem}
    .task-class{display:block;font-size:1.18rem;font-weight:750;line-height:1.35;color:#193a63;margin-bottom:3px}
    .task-origin{display:block;font-size:.76rem;font-weight:500;letter-spacing:.03em;color:#64748b;margin-bottom:7px}
    .due-overdue{color:#b42332!important;font-weight:750}
    .canvas-meta,.row{display:flex;flex-wrap:wrap;align-items:center;gap:8px 12px;margin-top:6px;line-height:1.5}
    .canvas-open{display:inline-flex;align-items:center;min-height:44px;padding:8px 13px;border-radius:8px;background:#1659a2;color:white;font-weight:600;text-decoration:none}
    input,select,textarea,button{font:inherit;padding:10px;border-radius:7px;border:1px solid #9baec4}
    button{background:#1659a2;color:white;border:0;cursor:pointer;min-height:44px}
    input,select,textarea{min-height:44px;box-sizing:border-box}
    a:focus-visible,button:focus-visible,input:focus-visible,select:focus-visible,textarea:focus-visible,summary:focus-visible{outline:3px solid #e19a20;outline-offset:3px}
    button:disabled{opacity:.65;cursor:not-allowed}
    summary{cursor:pointer;padding:10px 4px;min-height:44px;box-sizing:border-box;font-weight:600}
    details[open]>summary{margin-bottom:12px}
    @media(hover:hover){button:hover{filter:brightness(.92)}}
    button.secondary{background:#e5edf7;color:#193a63}button.danger{background:#9f2936}
    label{display:block;margin:8px 0 4px}form.inline{display:inline}
    small{color:#52647b}.done{text-decoration:line-through;color:#64748b}
    a{color:#1659a2}.status{font-weight:600}.unchecked{color:#a34d00}.checked{color:#147044}
    input[type=text]{min-width:220px}
    @media(max-width:580px){input,select,button{max-width:100%}.row>*{flex:1 1 170px}header nav a{min-height:44px;display:inline-flex;align-items:center}}
    @media(prefers-reduced-motion:reduce){*,*::before,*::after{scroll-behavior:auto!important;transition:none!important;animation:none!important}}
    """
    return HTMLResponse(
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>{esc(title)} · SyncCanvas</title><style>{css}</style></head><body>'
        '<a class="skip-link" href="#main-content">Skip to main content</a>'
        '<header><h1>SyncCanvas</h1><nav aria-label="Main navigation"><a href="/afternoon">My Afternoon</a>'
        '<a href="/add">Add Information</a><a href="/review">School Check-Out</a>'
        '<a class="parent-link" href="/parent">Parent Review</a>'
        '<a href="/settings">Settings</a></nav></header>'
        f'<main id="main-content"><h2>{esc(title)}</h2>{content}'
        '<p><small>Local prototype only · No accounts or cloud sync yet · Do not publish online</small></p>'
        '</main></body></html>'
    )

def sync_controls(return_to: str, *, heading: str = "Canvas updates") -> str:
    """A shared read-only status and manual sync action for family pages."""
    status = present_sync_status(sync_coordinator.status())
    raw = sync_coordinator.status()
    with db() as conn:
        try:
            last_saved = conn.execute("SELECT last_success_at FROM canvas_sync_audit WHERE id=1").fetchone()
        except sqlite3.OperationalError as exc:
            if "no such table" not in str(exc):
                raise
            last_saved = None
    pieces = [f'<section class="panel"><h3>{esc(heading)}</h3>',
              (f'<p><small>Last successful Canvas import: {esc(last_saved[0])} UTC. '
               'Information may be out of date until the next successful update.</small></p>'
               if last_saved else '<p><small>No successful Canvas import recorded yet. Canvas information may be incomplete.</small></p>'),
              f'<p><strong>{esc(status.label)}</strong> — {esc(status.message)}</p>']
    if raw.finished_at and raw.state == SyncState.SUCCESS:
        try:
            from datetime import timezone
            stamp = datetime.fromisoformat(raw.finished_at).astimezone().strftime('%m/%d/%Y %I:%M %p')
        except (ValueError, TypeError):
            stamp = str(raw.finished_at)
        pieces.append(f'<p><small>Last successful update: {esc(stamp)}</small></p>')
    elif raw.finished_at and raw.state == SyncState.ERROR:
        pieces.append('<p role="alert"><small>Canvas is temporarily unavailable. Your saved tasks remain available. Try checking for updates again later.</small></p>')
    if status.state not in (SyncState.NOT_CONFIGURED.value, SyncState.RUNNING.value):
        pieces.append('<form method="post" action="/sync/run">'
                      f'<input type="hidden" name="return_to" value="{esc(return_to)}">'
                      '<button type="submit">Check for updates</button></form>')
    if status.state == SyncState.NOT_CONFIGURED.value:
        pieces.append('<p><small>Canvas synchronization is not configured.</small></p>')
    if status.state == SyncState.RUNNING.value:
        pieces.append("""<p><small>Checking Canvas now. This page will refresh when finished.</small></p>
            <script>(function(){let failures=0;async function checkSync(){try{
            const response=await fetch('/api/sync/status',{cache:'no-store',headers:{'Accept':'application/json'}});
            if(!response.ok)throw Error('Status unavailable');const status=await response.json();failures=0;
            if(status.state!=='running'){window.location.reload();return;}
            }catch(error){failures++;if(failures>=5){window.location.reload();return;}}
            window.setTimeout(checkSync,1500);}window.setTimeout(checkSync,1500);}());</script>""")
    pieces.append('</section>')
    return ''.join(pieces)

def today():
    return family_today().isoformat()

def labeled_input(label, name, *, input_type="text", value="", required=False):
    """Reusable accessible labeled field; escape all dynamic HTML attributes."""
    field_id = "field-" + "".join(c if c.isalnum() or c in "-_" else "-" for c in name)
    return (f'<label for="{esc(field_id)}">{esc(label)}</label>'
            f'<input id="{esc(field_id)}" type="{esc(input_type)}" name="{esc(name)}"'
            f' value="{esc(value or "")}"{" required" if required else ""}>')


def deadline_fields(due_date=""):
    """One optional due date for manually added tasks."""
    return labeled_input("Due date (optional)", "due_date", input_type="date", value=due_date)


def deadline_label(item):
    due = item["due_date"]
    return f'Due {friendly_date(due)}' if due else ''


def deadline_html(item):
    label = deadline_label(item)
    if not label:
        return ''
    return f'<p class="muted"><small>{esc(label)}</small></p>'


def options(selected=""):
    return "".join(f'<option value="{esc(kind)}"{" selected" if kind == selected else ""}>{esc(kind)}</option>' for kind in KINDS)

def get_active_classes(conn):
    """Show classes in bell-period order, including on weekends and days off.

    Today's meeting periods take priority when school is open. Other classes
    follow in their normal bell-period order; unassigned classes come last.
    """
    day = family_today().isoformat()
    weekday = str(family_today().weekday())
    try:
        closed = conn.execute(
            "SELECT kind FROM school_days WHERE day=?", (day,)
        ).fetchone()
        use_today = not (closed and closed["kind"] == "closed")
    except sqlite3.OperationalError as exc:
        if "no such table" not in str(exc):
            raise
        use_today = True

    try:
        # Pick ONE period per class so its label and start time always agree.
        # On non-school days, fall back to the normal bell schedule rather
        # than dropping every class into the manual sort order.
        return conn.execute("""
            WITH ranked AS (
                SELECT cp.class_id, p.label AS period_label,
                    COALESCE(sp.start_time, p.start_time) AS period_start,
                    ROW_NUMBER() OVER (
                        PARTITION BY cp.class_id
                        ORDER BY
                            CASE WHEN ?=1 AND instr(p.weekdays, ?) > 0
                                 THEN 0 ELSE 1 END,
                            CASE WHEN ?=1 AND instr(p.weekdays, ?) > 0
                                 THEN COALESCE(sp.start_time, p.start_time)
                                 ELSE p.start_time END,
                            p.start_time, p.id
                    ) AS rn
                FROM class_periods cp
                JOIN bell_periods p ON p.id=cp.period_id
                LEFT JOIN school_day_periods sp
                    ON sp.period_id=p.id AND sp.day=?
            )
            SELECT c.id, c.name,
                   CASE WHEN ?=1 THEN r.period_label ELSE NULL END AS period_label,
                   CASE WHEN ?=1 THEN r.period_start ELSE NULL END AS period_start
            FROM classes c
            LEFT JOIN ranked r ON r.class_id=c.id AND r.rn=1
            WHERE c.enabled=1 AND c.archived=0
            ORDER BY CASE WHEN r.period_start IS NULL THEN 1 ELSE 0 END,
                     r.period_start, c.name COLLATE NOCASE, c.id
        """, (int(use_today), weekday, int(use_today), weekday, day,
              int(use_today), int(use_today))).fetchall()
    except sqlite3.OperationalError as exc:
        if "no such table" not in str(exc):
            raise
        return conn.execute(
            """SELECT id,name,NULL AS period_label,NULL AS period_start
               FROM classes WHERE enabled=1 AND archived=0
               ORDER BY name COLLATE NOCASE,id"""
        ).fetchall()

def ensure_canvas_planning(conn):
    """Family-only scheduling choices; never written back to Canvas."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS canvas_family_planning (
            assignment_id INTEGER PRIMARY KEY,
            planning_date TEXT,
            show_now INTEGER NOT NULL DEFAULT 0
        )
    """)


def effective_canvas_date(item):
    return item["planning_date"] or item["due_date"]


def afternoon_bucket(item, cutoff, far_cutoff):
    if item["show_now"]:
        return "current"
    due = effective_canvas_date(item)
    if not due:
        return "undated"
    if due <= cutoff:
        return "current"
    if due <= far_cutoff:
        return "future"
    return "far"


@router.post("/parent/canvas/{assignment_id}/planning")
def save_canvas_planning(
    assignment_id: int,
    planning_date: str = Form(""),
    show_now: str = Form(""),
):
    planning_date = planning_date.strip()
    if planning_date:
        try:
            date.fromisoformat(planning_date)
        except ValueError:
            raise HTTPException(400, "Invalid planning date")
    with db() as conn:
        ensure_canvas_planning(conn)
        if not conn.execute("SELECT 1 FROM canvas_assignments WHERE id=?", (assignment_id,)).fetchone():
            raise HTTPException(404, "Canvas assignment not found")
        conn.execute("""
            INSERT INTO canvas_family_planning(assignment_id,planning_date,show_now)
            VALUES(?,?,?)
            ON CONFLICT(assignment_id) DO UPDATE SET
                planning_date=excluded.planning_date,show_now=excluded.show_now
        """, (assignment_id, planning_date or None, int(show_now == "yes")))
    from fastapi.responses import RedirectResponse
    return RedirectResponse("/parent", status_code=303)


def canvas_planning_editor(assignment):
    aid = assignment["id"]
    planned = assignment["planning_date"] or ""
    selected = " checked" if assignment["show_now"] else ""
    return (f'<form method="post" action="/parent/canvas/{aid}/planning">'
            f'<label for="plan-{aid}">Parent planning date</label>'
            f'<input id="plan-{aid}" type="date" name="planning_date" value="{esc(planned)}">'
            f'<label><input type="checkbox" name="show_now" value="yes"{selected}> Show now</label>'
            '<button type="submit">Save planning</button></form>'
            + (f'<small>Teacher due: {esc(friendly_date(assignment["due_date"]))}</small>'
               if assignment["due_date"] else '<small>Teacher has not set a due date.</small>'))


def get_canvas_assignments(conn):
    ensure_canvas_planning(conn)
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(canvas_assignments)")}
    submitted = "a.canvas_submitted" if "canvas_submitted" in cols else "0"
    canvas_missing = "a.canvas_missing" if "canvas_missing" in cols else "0"
    reviewed = "a.review_dismissed" if "review_dismissed" in cols else "0"
    category = "a.family_category" if "family_category" in cols else "'auto'"
    missing = "a.missing_from_canvas" if "missing_from_canvas" in cols else "0"
    last_seen = "a.last_seen_at" if "last_seen_at" in cols else "NULL"
    return conn.execute(f"""SELECT a.id,a.title,a.due_date,a.due_at,a.html_url,
        a.submission_types,a.completed,{missing} AS missing_from_canvas,{last_seen} AS last_seen_at,{category} AS family_category,{submitted} AS canvas_submitted,{canvas_missing} AS canvas_missing,{reviewed} AS review_dismissed,c.id AS class_id,c.name AS class_name,c.sort_order,fp.planning_date,COALESCE(fp.show_now,0) AS show_now
        FROM canvas_assignments a LEFT JOIN canvas_family_planning fp ON fp.assignment_id=a.id JOIN canvas_course_links l ON l.canvas_course_id=a.canvas_course_id
        JOIN classes c ON c.id=l.class_id WHERE c.enabled=1 AND c.archived=0
        ORDER BY CASE WHEN a.due_date IS NULL OR a.due_date='' THEN 1 ELSE 0 END,
        a.due_date,a.due_at,a.title,a.id""").fetchall()

CANVAS_CATEGORIES = {"action": "Action needed", "assessment": "Assessment", "review": "Review / reference", "class": "In class", "unsorted": "Unsorted"}

def canvas_category(assignment):
    """Conservative suggestions, not assertions about teacher intent."""
    override = assignment["family_category"]
    if override in CANVAS_CATEGORIES:
        return override
    title = str(assignment["title"] or "").casefold()
    if any(term in title for term in ("answer key", "study guide", "reference", "review sheet")):
        return "review"
    if any(term in title for term in ("warmup", "warm-up", "exit ticket", "bellringer", "bell ringer")):
        return "class"
    if any(term in title for term in ("quiz", "test", "exam")):
        return "assessment"
    # A due date alone is not proof of homework. Submission requirements can
    # suggest an action, but an unsubmitted Canvas item still needs confirmation.
    try:
        types = json.loads(assignment["submission_types"] or "[]")
    except (TypeError, ValueError):
        types = []
    if any(t in types for t in ("online_upload", "online_text_entry", "online_url", "student_annotation")):
        return "action"
    return "unsorted"

def actionable_canvas(assignment):
    return canvas_category(assignment) == "action"

def canvas_category_tag(assignment):
    category = canvas_category(assignment)
    return f'<span class="category-tag">{esc(CANVAS_CATEGORIES[category])}</span>'

def canvas_category_editor(assignment):
    value = assignment["family_category"]
    opts = ['<option value="auto"' + (' selected' if value == 'auto' else '') + '>Suggested</option>']
    opts += [f'<option value="{key}"' + (' selected' if value == key else '') + f'>{esc(label)}</option>'
             for key,label in CANVAS_CATEGORIES.items()]
    return (f'<form class="category-form" method="post" action="/parent/canvas/{assignment["id"]}/category">'
            f'<label for="category-{assignment["id"]}">Parent classification</label>'
            f'<select id="category-{assignment["id"]}" name="category">{"".join(opts)}</select>'
            '<button class="secondary" type="submit">Save</button></form>')

def canvas_presence_label(assignment):
    if assignment["canvas_missing"]:
        return '<p class="muted" role="status">Canvas reports this submission as missing. Check Canvas for details.</p>'
    if assignment["missing_from_canvas"]:
        return '<p class="muted" role="status">Not found in the latest successful Canvas update. Saved family work is kept; check Canvas before assuming this was cancelled.</p>'
    return ""

def canvas_due_label(assignment):
    due = assignment["due_date"]
    if not due: return "No due date"
    if due < today() and actionable_canvas(assignment) and not assignment["missing_from_canvas"]: return f"Overdue · {friendly_date(due)}"
    if due == today(): return "Due today"
    return f"Due {friendly_date(due)}"

def submission_label(raw):
    labels = {"on_paper":"Turn in on paper","online_upload":"Upload a file",
        "online_text_entry":"Type an answer online","online_url":"Submit a website link",
        "online_quiz":"Online quiz","external_tool":"External tool",
        "discussion_topic":"Discussion","none":"No submission required","not_graded":"Not graded",
        "media_recording":"Record audio or video","student_annotation":"Annotate a document"}
    try: values = json.loads(raw or "[]")
    except (ValueError, TypeError): return "Submission method unavailable"
    if not isinstance(values,list) or not values: return "Submission method not specified"
    return " / ".join(labels.get(x,x.replace("_"," ").capitalize()) for x in values if isinstance(x,str))

def canvas_title_html(assignment):
    url = str(assignment["html_url"] or "").strip()
    title = esc(assignment["title"])
    if url.lower().startswith("https://"):
        return f'<a href="{esc(url)}" target="_blank" rel="noopener noreferrer">{title}</a>'
    return title

def canvas_assignment_html(assignment, *, show_class=False):
    url = str(assignment["html_url"] or "").strip()
    link = (f'<a class="canvas-open" href="{esc(url)}" target="_blank" rel="noopener noreferrer">Open in Canvas ↗</a>'
            if url.lower().startswith("https://") else "")
    prefix = f'<span class="task-class">{esc(assignment["class_name"])}</span>' if show_class else ""
    status = "Completed" if assignment["completed"] else canvas_due_label(assignment)
    if assignment["planning_date"] and not assignment["completed"]:
        status = f'Plan: {friendly_date(assignment["planning_date"])} · Teacher: {canvas_due_label(assignment)}'
    if assignment["show_now"] and not assignment["completed"]:
        status = "Show now · " + status
    due_class = "due-overdue" if not assignment["completed"] and status.startswith("Overdue") else ""
    return (f'<div class="canvas-card">{prefix}<strong>{canvas_title_html(assignment)}</strong>'
            f'<div class="canvas-meta"><small><span class="{due_class}">{esc(status)}</span> · '
            f'{esc(submission_label(assignment["submission_types"]))}</small>{canvas_category_tag(assignment)}{link}</div>'
            f'{canvas_presence_label(assignment)}</div>')

def completed_canvas_history(assignments):
    cutoff = (family_today()-timedelta(days=7)).isoformat()
    return [a for a in assignments if a["completed"] and a["due_date"] and a["due_date"]>=cutoff]

def canvas_history_html(assignments):
    recent = completed_canvas_history(assignments)
    parts = [f'<details class="panel"><summary>Recently completed Canvas assignments ({len(recent)})</summary>',
             '<p><small>Last 7 days by assignment due date; completion dates are not available yet.</small></p>']
    if not recent: parts.append('<p>No completed Canvas assignments due in the last 7 days.</p>')
    else: parts.extend(canvas_assignment_html(a,show_class=True) for a in reversed(recent))
    return "".join(parts)+"</details>"

def manual_entries(conn):
    columns={r["name"] for r in conn.execute("PRAGMA table_info(entries)")}
    origin="e.origin" if "origin" in columns else "'student' AS origin"
    planned="e.planned_date" if "planned_date" in columns else "NULL AS planned_date"
    linked=conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='entry_canvas_links'").fetchone()
    canvas=conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='canvas_assignments'").fetchone()
    if linked and canvas:
        relation="LEFT JOIN entry_canvas_links link ON link.entry_id=e.id LEFT JOIN canvas_assignments a ON a.id=link.canvas_assignment_id"
        linked_columns="a.title AS linked_canvas_title, a.id AS linked_canvas_id, a.due_date AS linked_canvas_due_date, a.missing_from_canvas AS linked_canvas_missing"
    else:
        relation=""
        linked_columns="NULL AS linked_canvas_title, NULL AS linked_canvas_id, NULL AS linked_canvas_due_date, 0 AS linked_canvas_missing"
    return conn.execute(f"""SELECT e.id,e.class_id,e.kind,e.details,e.done,e.parent_confirmed,
        e.coaching_note,e.progress,e.completed_at,e.due_date,{origin},{planned},c.name AS class_name,
        {linked_columns}
        FROM entries e JOIN classes c ON c.id=e.class_id {relation}
        WHERE e.kind!='Nothing Tonight' AND c.enabled=1 AND c.archived=0
        ORDER BY c.sort_order,c.id,e.id DESC""").fetchall()

def checkins_today(conn):
    return {r["class_id"]:r["nothing_tonight"] for r in conn.execute("""
        SELECT ch.class_id,ch.nothing_tonight FROM checkins ch JOIN classes c ON c.id=ch.class_id
        WHERE ch.day=? AND c.enabled=1 AND c.archived=0""",(today(),))}

def checkin_label(cid,checkins):
    return "Not checked yet" if cid not in checkins else "Nothing tonight" if checkins[cid] else "Checked today"

@router.get("/",response_class=HTMLResponse)
def student():
    with db() as conn:
        classes=get_active_classes(conn)
        try:
            school_exception=conn.execute('SELECT kind,note FROM school_days WHERE day=?',(today(),)).fetchone()
        except sqlite3.OperationalError as exc:
            if 'no such table' not in str(exc): raise
            school_exception=None
        canvas_assignments=get_canvas_assignments(conn)
        entries=manual_entries(conn)
        checkins=checkins_today(conn)
        try:
            lunch_activities=conn.execute("""SELECT a.id,a.name,p.label AS period_label,
                COALESCE((SELECT sp.start_time FROM school_day_periods sp WHERE sp.day=? AND sp.period_id=p.id),p.start_time) AS start_time,
                COALESCE((SELECT sp.end_time FROM school_day_periods sp WHERE sp.day=? AND sp.period_id=p.id),p.end_time) AS end_time
                FROM lunch_buddies a JOIN bell_periods p ON p.id=a.period_id
                WHERE instr(a.weekdays,?)>0 AND instr(p.weekdays,?)>0
                ORDER BY start_time,a.name,a.id""",
                (today(),today(),str(family_today().weekday()),str(family_today().weekday()))).fetchall()
        except sqlite3.OperationalError as exc:
            if "no such table" not in str(exc):
                raise
            lunch_activities=[]
        try:
            lunch_tasks=conn.execute("""SELECT t.*,a.name AS activity_name
                FROM lunch_tasks t JOIN lunch_buddies a ON a.id=t.activity_id
                ORDER BY t.id DESC""").fetchall()
        except sqlite3.OperationalError as exc:
            if "no such table" not in str(exc):
                raise
            lunch_tasks=[]
    if school_exception and school_exception['kind']=='closed':
        lunch_activities=[]
    tasks_by_lunch={}
    for task in lunch_tasks:
        tasks_by_lunch.setdefault(task['activity_id'], []).append(task)
    by_class={}
    for entry in entries: by_class.setdefault(entry["class_id"],[]).append(entry)
    canvas_by_class={}
    for assignment in canvas_assignments:
        if not assignment["completed"]: canvas_by_class.setdefault(assignment["class_id"],[]).append(assignment)
    parts=['<section class="panel"><h3>My tasks come first</h3><p><a class="canvas-open" href="/afternoon">Open today’s unified task plan →</a></p>'
           '<p><small>Canvas information is grouped by purpose in My Afternoon. This class view is for school check-out.</small></p></section>',
           sync_controls("/", heading="School updates")]
    if school_exception:
        kind_label='No school today' if school_exception['kind']=='closed' else 'Shortened / special school day'
        parts.append('<section class="panel"><h3>'+kind_label+'</h3><p>'+esc(school_exception['note'])+'</p></section>')
    if lunch_activities:
        parts.append('<section class="panel"><h3>Lunch Buddies today</h3>')
        for activity in lunch_activities:
            parts.append(f'<p><strong>{esc(activity["name"])}</strong> · Period {esc(activity["period_label"])} '
                         f'({esc(american_time(activity["start_time"]))}–{esc(american_time(activity["end_time"]))})</p>')
            aid=activity['id']
            for task in tasks_by_lunch.get(aid, []):
                status='Parent confirmed' if task['parent_confirmed'] else 'Waiting for parent review' if task['done'] else 'Not started'
                parts.append(f'<div class="class"><strong>{esc(task["details"])}</strong> · {status}</div>')
                if task['coaching_note']:
                    parts.append(f'<p><small>Parent note: {esc(task["coaching_note"])}</small></p>')
            parts.append(f'<form method="post" action="/parent/lunch-buddies/{aid}/tasks">'
                         '<label>What happened or what needs to be done?</label>'
                         '<input type="text" name="details" maxlength="300" required placeholder="Add a note or task">'
                         '<button type="submit">Add task</button></form>')
        parts.append('</section>')
    if not classes:
        parts.append('<section class="panel"><p>No active classes are available yet. Classes are managed from the Parent page.</p></section>')
    for cls in classes:
        cid=cls["id"]
        css="unchecked" if cid not in checkins else "checked"
        parts.append(f'<section class="panel"><h3>{esc(cls["name"])}' + (f' · Period {esc(cls["period_label"])} ({esc(american_time(cls["period_start"]))})' if cls["period_label"] else '') + '</h3>'
                     f'<p class="status {css}">{checkin_label(cid,checkins)}</p>')
        if canvas_by_class.get(cid):
            parts.append('<h4>Canvas information to check</h4>')
            parts.extend(canvas_assignment_html(a) for a in canvas_by_class[cid])
        for item in by_class.get(cid,[]):
            status=' class="done"' if item["done"] else ''
            state='Parent confirmed' if item["parent_confirmed"] else 'Waiting for parent review' if item["done"] else 'Not Started'
            note=f'<p><small>Parent note: {esc(item["coaching_note"])}</small></p>' if item["coaching_note"] else ''
            parts.append(f'<div class="class"><span{status}><strong>{esc(item["kind"])}</strong> — '
                         f'{esc(item["details"])}</span> · {esc(state)}{deadline_html(item)}{note}</div>')
        parts.append(f'''<details class="class-entry"><summary>Add homework or a note</summary><form method="post" action="/classes/{cid}/entries">
            <label for="kind-{cid}">What needs to happen?</label><select id="kind-{cid}" name="kind">{options()}</select>
            <label for="details-{cid}">What exactly? (required)</label>
            <input type="text" id="details-{cid}" name="details" required maxlength="300" placeholder="e.g. Questions 1–10">
            {deadline_fields()}
            <input type="hidden" name="submission_token" value="{secrets.token_hex(32)}">
            <button type="submit">Add task &amp; check in</button></form></details>
            <div class="row"><form class="inline" method="post" action="/classes/{cid}/nothing">
            <button class="secondary" type="submit">Nothing Tonight</button></form>
            <form class="inline" method="post" action="/classes/{cid}/checkin">
            <button class="secondary" type="submit">Checked — still deciding</button></form></div></section>''')
    parts.append(canvas_history_html(canvas_assignments))
    return layout("My Classes","".join(parts))

@router.get("/add",response_class=HTMLResponse)
def quick_add():
    """Quick capture using the existing validated manual-entry endpoint."""
    with db() as conn:
        classes=get_active_classes(conn)
    parts=['<section class="panel"><h3>Something I still need to do</h3>',
           '<p>A few words are enough. A parent can fill in details later.</p>']
    if not classes:
        parts.append('<p>No active classes. Ask a parent to set up classes in Settings.</p>')
    else:
        parts.append('<form id="quick-entry" method="post" action="/add">'
                     '<label for="quick-class">Class</label><select id="quick-class" name="class_id" required>')
        parts.extend(f'<option value="{c["id"]}">{esc(c["name"])}</option>' for c in classes)
        parts.append('</select><label for="quick-kind">What kind of work?</label>'
                     '<select id="quick-kind" name="kind">'
                     '<option value="Finish Classwork" selected>Something I still need to do</option>'
                     '<option value="Homework">Homework</option>'
                     '<option value="Study">Study or review</option>'
                     '<option value="Prepare for Quiz">Prepare for quiz</option>'
                     '<option value="Ask Teacher">Ask teacher</option></select>'
                     '<label for="quick-details">A few words</label>'
                     '<input id="quick-details" name="details" type="text" maxlength="300" required '
                     'placeholder="e.g. finish problems 4–8" autofocus>'
                     + deadline_fields()
                     + f'<input type="hidden" name="submission_token" value="{secrets.token_hex(32)}">'
                     '<p><button type="submit">Save</button></p></form>')
    parts.append('<p><a href="/">Detailed class check-in</a></p></section>')
    return layout("Add Information","".join(parts))


@router.get("/review",response_class=HTMLResponse)
def review():
    """Quick end-of-day double-check of each class, not a second task list."""
    with db() as conn:
        classes = get_active_classes(conn)
        entries = manual_entries(conn)
        assignments = get_canvas_assignments(conn)
        school_reviews = {r["class_id"]: r for r in conn.execute(
            "SELECT class_id,outcome,reviewed_at FROM school_reviews WHERE day=?", (today(),))}
        questions = {r["class_id"]: r for r in conn.execute(
            "SELECT class_id,question,resolved FROM class_questions WHERE day=?", (today(),))}
        corrections = {}
        for change in conn.execute("""SELECT class_id,previous_outcome,new_outcome,corrected_at
            FROM checkout_corrections WHERE day=? ORDER BY id DESC""", (today(),)):
            corrections.setdefault(change["class_id"], []).append(change)
        packing = conn.execute("SELECT * FROM checkout_items WHERE day=? ORDER BY id", (today(),)).fetchall()
        paper = conn.execute("SELECT * FROM paper_reviews WHERE day=?", (today(),)).fetchone()

    by_class = {}
    for entry in entries:
        by_class.setdefault(entry["class_id"], []).append(entry)
    canvas_by_class = {}
    for assignment in assignments:
        if not assignment["completed"]:
            canvas_by_class.setdefault(assignment["class_id"], []).append(assignment)

    completed = sum(cls["id"] in school_reviews for cls in classes)
    parts = [
        '<section class="panel"><h3>End-of-Day Check-Out</h3>',
        '<p>Before you leave, look at each class. Did you write down everything '
        'you need to do at home, and do you have what you need to bring home?</p>',
        f'<p><strong>{completed} of {len(classes)}</strong> classes reviewed today.</p></section>',
    ]
    with db() as conn:
        class_materials = conn.execute("""SELECT m.id,m.class_id,m.description,
            COALESCE(p.packed,0) AS packed FROM class_materials m
            JOIN classes c ON c.id=m.class_id
            LEFT JOIN material_packing p ON p.material_id=m.id AND p.day=?
            WHERE c.enabled=1 AND c.archived=0 ORDER BY c.sort_order,c.id,m.id""",
            (today(),)).fetchall()
    materials_by_class = {}
    for material in class_materials:
        materials_by_class.setdefault(material["class_id"], []).append(material)
    for cls in classes:
        cid = cls["id"]
        record = school_reviews.get(cid)
        is_reviewed = record is not None
        parts.append(f'<section class="panel"><h3 class="task-class">{esc(cls["name"])}</h3>')
        status = ({"reviewed": "Checked", "nothing": "Checked — nothing to do",
                   "needs_followup": "Needs clarification"}.get(record["outcome"], "Unchecked")
                  if record else "Unchecked")
        parts.append(f'<p><strong>{esc(status)}</strong></p>')
        if record:
            parts.append(f'<p><small>Last checked: {esc(record["reviewed_at"])} UTC</small></p>')
        if not is_reviewed:
            parts.append(
                f'<form method="post" action="/school/classes/{cid}/review">'
                '<input type="hidden" name="outcome" value="reviewed">'
                '<button type="submit">✓ I reviewed this class</button></form>'
            )
        else:
            parts.append(
                f'<form method="post" action="/school/classes/{cid}/review">'
                '<input type="hidden" name="outcome" value="reviewed">'
                '<button class="secondary" type="submit">Review again</button></form>'
            )
        parts.append(f'''<details><summary>Change checkout status</summary>
            <form method="post" action="/school/classes/{cid}/review">
            <label for="outcome-{cid}">Class status</label>
            <select id="outcome-{cid}" name="outcome">
            <option value="reviewed">Checked</option>
            <option value="nothing">Nothing to do</option>
            <option value="needs_followup">Needs clarification</option>
            </select><button type="submit">Save status</button></form></details>''')
        if corrections.get(cid):
            parts.append('<details><summary>Earlier corrections</summary><ul>')
            for change in corrections[cid]:
                parts.append(f'<li>{esc(change["previous_outcome"])} → '
                             f'{esc(change["new_outcome"])} · '
                             f'{esc(change["corrected_at"])} UTC</li>')
            parts.append('</ul></details>')
        current = by_class.get(cid, [])
        canvas = canvas_by_class.get(cid, [])
        if current:
            parts.append('<p>What you wrote down:</p><ul>')
            parts.extend(
                f'<li>{esc(entry["kind"])} — {esc(entry["details"])}'
                + (f' · {esc(deadline_label(entry))}' if deadline_label(entry) else '')
                + '</li>' for entry in current
            )
            parts.append('</ul>')
        elif not canvas:
            parts.append('<p>No work recorded for this class. Is that right?</p>')
        if canvas:
            parts.append('<p>Canvas assignments to double-check:</p>')
            parts.extend(canvas_assignment_html(a) for a in canvas)
        parts.append('<details><summary>Materials for this class</summary>'
                     '<p>Keep this list for future school days. Packing checks reset each day.</p>')
        for material in materials_by_class.get(cid, []):
            mid = material["id"]
            packed = bool(material["packed"])
            parts.append(f'<div class="class"><strong>{esc(material["description"])}</strong> — '
                         + ('Packed today' if packed else 'Not packed today')
                         + f'<form class="inline" method="post" action="/school/materials/{mid}/packed">'
                         + f'<input type="hidden" name="packed" value="{"" if packed else "yes"}">'
                         + f'<button class="secondary" type="submit">{"Undo packed" if packed else "Mark packed"}</button></form> '
                         + f'<form class="inline" method="post" action="/school/materials/{mid}/delete">'
                         + '<button class="secondary" type="submit">Remove</button></form></div>')
        parts.append(f'<form method="post" action="/school/classes/{cid}/materials">'
                     f'<label for="material-{cid}">Add a reusable material</label>'
                     f'<input id="material-{cid}" name="description" maxlength="120" required '
                     'placeholder="e.g. Math workbook">'
                     '<button type="submit">Add material</button></form></details>')
        parts.append(
            '<p>Forgot to write something down? '
            '<a href="/add">Add it to your class notes</a>.</p>'
        )
        question = questions.get(cid)
        if question and question["question"]:
            parts.append(f'<p><strong>Reminder:</strong> {esc(question["question"])}'
                         + (' (resolved)' if question["resolved"] else '') + '</p>')
        parts.append(
            f'<form method="post" action="/school/classes/{cid}/question">'
            '<label>Anything missing or unclear? (optional)</label>'
            f'<input type="text" name="question" maxlength="300" value="{esc(question["question"] if question else "")}" '
            'placeholder="e.g. Need to bring math workbook home">'
            '<button class="secondary" type="submit">Save note</button></form>'
        )
        parts.append('</section>')

    parts.append('<section class="panel"><h3>What must go home?</h3>'
                 '<p>Add books, papers, or devices you need tonight. Mark each one packed.</p>')
    for item in packing:
        parts.append(f'<p>{esc(item["description"])} ({esc(item["item_type"])}) — '
                     + ('Packed' if item['ready'] else 'Not packed') + '</p>')
        parts.append(f'<form class="inline" method="post" action="/school/packing/{item["id"]}/ready">'
                     f'<input type="hidden" name="ready" value="{ "" if item["ready"] else "yes" }">'
                     f'<button class="secondary" type="submit">{ "Undo packed" if item["ready"] else "Packed" }</button></form>')
    parts.append('''<details><summary>Add something to bring home</summary>
        <form method="post" action="/school/packing/add">
        <label>Type</label><select name="item_type">
        <option value="book">Book</option><option value="paper">Paper</option>
        <option value="device">Device</option><option value="other">Other</option></select>
        <label>What do you need?</label><input name="description" maxlength="120" required>
        <button type="submit">Add to packing list</button></form></details></section>''')
    # Older paper-check notes remain visible, without requiring a second checklist.
    if paper and paper["notes"]:
        parts.append('<section class="panel"><h3>Earlier paper note</h3>'
                     f'<p>{esc(paper["notes"])}</p></section>')
    if classes and completed == len(classes):
        parts.append('<section class="panel"><p><strong>All classes reviewed.</strong> '
                     'Check your bag and you are ready to head home.</p></section>')
    return layout("School Check-Out", "".join(parts))

@router.get("/afternoon",response_class=HTMLResponse)
@router.get("/home",response_class=HTMLResponse)
def home():
    with db() as conn:
        ensure_today(conn)
        canvas_assignments=get_canvas_assignments(conn)
        entries=manual_entries(conn)
        try:
            lunch_open=conn.execute("""SELECT t.id,t.details,a.name AS activity_name
                FROM lunch_tasks t JOIN lunch_buddies a ON a.id=t.activity_id
                WHERE t.done=0 ORDER BY t.id DESC""").fetchall()
        except sqlite3.OperationalError as exc:
            if "no such table" not in str(exc): raise
            lunch_open=[]
    classes = []
    with db() as conn:
        classes = get_active_classes(conn)
    cutoff = (family_today() + timedelta(days=2)).isoformat()
    far_cutoff = (family_today() + timedelta(days=60)).isoformat()
    incomplete = [a for a in canvas_assignments if not a["completed"]]
    open_entries = [e for e in entries if not e["done"]]
    waiting = [e for e in entries if e["done"] and not e["parent_confirmed"]]
    linked_ids = {e["linked_canvas_id"] for e in open_entries if e["linked_canvas_id"] is not None}
    buckets = {key: {} for key in ("current", "future", "far", "undated")}
    for assignment in incomplete:
        if assignment["id"] in linked_ids:
            continue
        bucket = afternoon_bucket(assignment, cutoff, far_cutoff)
        buckets[bucket].setdefault(assignment["class_id"], []).append(("canvas", assignment))
    for item in open_entries:
        due = item["planned_date"] or item["due_date"]
        if item["planned_date"] and item["planned_date"] > cutoff:
            bucket = "far" if item["planned_date"] > far_cutoff else "future"
        elif not due:
            bucket = "current"  # Family-created tasks need attention until completed.
        elif due <= cutoff:
            bucket = "current"
        elif due <= far_cutoff:
            bucket = "future"
        else:
            bucket = "far"
        buckets[bucket].setdefault(item["class_id"], []).append(("manual", item))

    def task_html(item):
        state = item["progress"] or "not_started"
        origin = "Parent added" if item["origin"] == "parent" else "Added information"
        return (f'<article class="task-card"><span class="task-origin">{origin}</span>'
                f'<h4>{esc(item["details"])}</h4><p class="muted">{esc(item["kind"])}</p>'
                f'{deadline_html(item)}'
                f'<form class="task-progress" method="post" action="/entries/{item["id"]}/progress">'
                f'<label for="progress-{item["id"]}">Progress</label>'
                f'<select id="progress-{item["id"]}" name="progress">'
                f'<option value="not_started"{" selected" if state=="not_started" else ""}>Not started</option>'
                f'<option value="in_progress"{" selected" if state=="in_progress" else ""}>In progress</option>'
                '<option value="done">Done</option></select>'
                '<button type="submit">Save progress</button></form>'
                + (f'<p><small>Parent note: {esc(item["coaching_note"])}</small></p>'
                   if item["coaching_note"] else "") + '</article>')

    def render_bucket(key):
        for cls in classes:
            items = buckets[key].get(cls["id"], [])
            if not items:
                continue
            label = (f'Period {esc(cls["period_label"])} — ' if cls["period_label"] else "")
            parts.append(f'<section class="panel"><h3>{label}{esc(cls["name"])} ({len(items)})</h3>')
            def sort_key(pair):
                kind, obj = pair
                due = (obj["planned_date"] or obj["due_date"]) if kind == "manual" else effective_canvas_date(obj)
                return (due is None, due or "9999-12-31", 0 if kind == "manual" else 1,
                        str(obj["details"] if kind == "manual" else obj["title"]).casefold())
            for kind, obj in sorted(items, key=sort_key):
                parts.append(task_html(obj) if kind == "manual" else canvas_assignment_html(obj))
            parts.append('</section>')

    parts = ['<section class="panel"><h3>Today and the next two days</h3>'
             '<p>Classes are in school-period order. Future Canvas work is grouped below. '
             'A parent can change a planning date or select Show now in Parent Review.</p>'
             f'<p><strong>{len(waiting)}</strong> tasks awaiting parent confirmation · '
             '<a href="/add">Add something I still need to do</a></p></section>']
    render_bucket("current")
    if not any(buckets["current"].values()) and not lunch_open:
        parts.append('<section class="panel"><p>No work due in the next two days.</p></section>')
    if lunch_open:
        parts.append('<section class="panel"><h3>Lunch Buddies tasks</h3>')
        for task in lunch_open:
            parts.append(f'<article class="task-card"><strong>{esc(task["activity_name"])}</strong>'
                         f'<h4>{esc(task["details"])}</h4>'
                         f'<form method="post" action="/parent/lunch-buddies/tasks/{task["id"]}/done">'
                         '<button type="submit">Done</button></form></article>')
        parts.append('</section>')
    for key, title in (("future", "Future work (3–60 days)"),
                       ("far", "Far future (61+ days)"),
                       ("undated", "No due date")):
        count = sum(len(v) for v in buckets[key].values())
        if count:
            parts.append(f'<details class="panel"><summary>{title} ({count})</summary>')
            render_bucket(key)
            parts.append('</details>')
    parts.append(canvas_history_html(canvas_assignments))
    return layout("My Afternoon","".join(parts))

@router.get("/parent",response_class=HTMLResponse)
def parent():
    with db() as conn:
        classes=get_active_classes(conn)
        checkins=checkins_today(conn)
        tasks=manual_entries(conn)
        open_questions=conn.execute("""SELECT q.class_id,q.question,c.name AS class_name
            FROM class_questions q JOIN classes c ON c.id=q.class_id
            WHERE q.day=? AND q.resolved=0 AND q.question!='' ORDER BY c.sort_order,c.id""",(today(),)).fetchall()
        school_review_count=conn.execute("SELECT COUNT(*) FROM school_reviews WHERE day=?",(today(),)).fetchone()[0]
        paper_review=conn.execute("SELECT pocket_checked,backpack_checked FROM paper_reviews WHERE day=?",(today(),)).fetchone()
        linked_choices=conn.execute("""SELECT a.id,a.title,l.class_id
            FROM canvas_assignments a JOIN canvas_course_links l ON l.canvas_course_id=a.canvas_course_id
            ORDER BY a.title""").fetchall()
        try:
            lunch_tasks=conn.execute("""SELECT t.*,a.name AS activity_name
                FROM lunch_tasks t JOIN lunch_buddies a ON a.id=t.activity_id
                ORDER BY t.id DESC""").fetchall()
        except sqlite3.OperationalError as exc:
            if "no such table" not in str(exc):
                raise
            lunch_tasks=[]
    tasks_by_class={}
    for task in tasks: tasks_by_class.setdefault(task["class_id"],[]).append(task)
    checked_count=sum(c["id"] in checkins for c in classes)
    open_count=sum(not t["done"] for t in tasks)
    awaiting_count=sum(t["done"] and not t["parent_confirmed"] for t in tasks)
    missing=[c for c in classes if c["id"] not in checkins]
    ask_teacher=[t for t in tasks if t["kind"]=="Ask Teacher" and not t["done"]]
    parts=['<section class="panel"><h3>Afternoon review</h3>',
           f'<p><strong>{checked_count}/{len(classes)}</strong> classes checked today · '
           f'<strong>{open_count}</strong> unfinished tasks · '
           f'<strong>{awaiting_count}</strong> awaiting parent confirmation · '
           f'<strong>{len(missing)+len(ask_teacher)}</strong> attention items</p>',
           '<p><small>Class check-ins apply to today; unfinished tasks can be from earlier days. '
           'Archived and disabled classes are excluded from the daily review.</small></p>',
           '<p><a href="/afternoon">View shared afternoon plan</a> · '
           '<a href="/settings">Configure SyncCanvas</a> · <a href="/parent/classes">Manage Classes</a></p></section>']
    parts.append(sync_controls("/parent"))
    # Supportive attention cues, never a score or an inferred grade.
    with db() as conn:
        canvas_attention = get_canvas_assignments(conn)
    late_manual = [t for t in tasks if not t["done"] and t["due_date"] and t["due_date"] < today()]
    late_canvas = [a for a in canvas_attention if not a["completed"] and actionable_canvas(a) and a["due_date"] and a["due_date"] < today()]
    needs_help = [t for t in tasks if not t["done"] and t["progress"] == "stuck"]
    parts.append('<section class="panel"><h3>Work that may need attention</h3>'
                 '<p>These are reminders to check in together, not grades or penalties.</p>')
    if not (late_manual or late_canvas or needs_help):
        parts.append('<p>No late or stuck work recorded.</p>')
    else:
        if late_manual or late_canvas:
            parts.append('<h4>Past due — check together</h4><ul>')
            for task in late_manual:
                parts.append(f'<li>{esc(task["class_name"])}: {esc(task["details"])} '
                             f'(due {esc(friendly_date(task["due_date"]))})</li>')
            for assignment in late_canvas:
                parts.append(f'<li>{esc(assignment["class_name"])}: {canvas_title_html(assignment)} '
                             f'(due {esc(friendly_date(assignment["due_date"]))})</li>')
            parts.append('</ul>')
        if needs_help:
            parts.append('<h4>Needs help — ask what is blocking progress</h4><ul>')
            for task in needs_help:
                parts.append(f'<li>{esc(task["class_name"])}: {esc(task["details"])}</li>')
            parts.append('</ul>')
    parts.append('</section>')
    review_items = [a for a in canvas_attention if a["canvas_submitted"] and not a["review_dismissed"]]
    parts.append('<section class="panel"><h3>Canvas submissions to review</h3>'
                 '<p>Submitted in Canvas and counted as complete. Check the original assignment if you want; grades are not required.</p>')
    if not review_items:
        parts.append('<p>No Canvas submissions awaiting review.</p>')
    for assignment in review_items:
        parts.append(f'<div class="canvas-card"><strong>{canvas_title_html(assignment)}</strong> '
                     f'<small>({esc(assignment["class_name"])}) · Needs review</small>'
                     f'<form method="post" action="/parent/canvas/{assignment["id"]}/review">'
                     '<button type="submit">Reviewed</button></form></div>')
    parts.append('</section>')
    parts.append('<section class="panel"><h3>Sort Canvas information</h3>'
                 '<p>Suggested classifications are editable. Your choice survives Canvas updates. '
                 'An item marked Review, In class, or Unsorted is never flagged as overdue homework.</p>')
    for assignment in canvas_attention:
        if assignment["completed"]: continue
        parts.append(f'<div class="compact-canvas"><strong>{canvas_title_html(assignment)}</strong> '
                     f'<small>({esc(assignment["class_name"])})</small> '
                     f'{canvas_category_tag(assignment)}{canvas_presence_label(assignment)}{canvas_category_editor(assignment)}{canvas_planning_editor(assignment)}' 
                     f'<form method="post" action="/parent/canvas/{assignment["id"]}/add-task">'
                     '<label>Turn into a family task</label>'
                     '<select name="kind"><option value="Study">Study</option>'
                     '<option value="Homework">Homework</option>'
                     '<option value="Review">Review</option></select>'
                     '<button type="submit">Add to My Tasks</button></form></div>')
    parts.append('</section>')
    parts.append('<section class="panel"><h3>School follow-up</h3>'
                 f'<p>{school_review_count}/{len(classes)} classes have a saved school review today. '
                 f'Pocket checked: {"yes" if paper_review and paper_review[0] else "no"}. '
                 f'Backpack checked: {"yes" if paper_review and paper_review[1] else "no"}.</p>')
    if open_questions:
        parts.append('<h4>Questions to resolve</h4><ul>')
        parts.extend(f'<li><strong>{esc(q["class_name"])}</strong>: {esc(q["question"])}</li>' for q in open_questions)
        parts.append('</ul>')
    else:
        parts.append('<p>No unresolved questions recorded today.</p>')
    parts.append('<p><a href="/review">Open School Check-Out</a></p></section>')
    if classes:
        parts.append('<section class="panel"><h3>Add a task to the afternoon plan</h3>'
                     '<p>Parent-added tasks appear on the same checklist as student tasks.</p>'
                     '<form method="post" action="/parent/tasks/add">'
                     '<label for="parent-class">Class</label><select id="parent-class" name="class_id">')
        parts.extend(f'<option value="{c["id"]}">{esc(c["name"])}</option>' for c in classes)
        parts.append('</select><label for="parent-kind">Type</label><select id="parent-kind" name="kind">'
                     + options('Study') + '</select>'
                     '<label for="parent-details">What needs doing?</label>'
                     '<input id="parent-details" name="details" maxlength="300" required>'
                     + deadline_fields()
                     + '<label for="parent-date">Work on (optional)</label>'
                     '<input id="parent-date" name="planned_date" type="date">'
                     '<p><button type="submit">Add to plan</button></p></form></section>')
    if not classes:
        parts.append('<section class="panel"><p>No active classes yet. <a href="/parent/classes">Manage Classes</a> to add or enable classes.</p></section>')
    else:
        parts.append('<section class="panel"><h3>All classes</h3>')
        for cls in missing+[c for c in classes if c["id"] in checkins]:
            cid=cls["id"]
            css="unchecked" if cid not in checkins else "checked"
            parts.append(f'<div class="class"><strong>{esc(cls["name"])}</strong>' + (f' · Period {esc(cls["period_label"])}' if cls["period_label"] else '') + ' — '
                         f'<span class="status {css}">{esc(checkin_label(cid,checkins))}</span>')
            unfinished=[t for t in tasks_by_class.get(cid,[]) if not t["done"]]
            if unfinished:
                parts.append('<ul>')
                parts.extend(f'<li>{esc(t["kind"])} — {esc(t["details"])}' + (f' · {esc(deadline_label(t))}' if deadline_label(t) else '') + '</li>' for t in unfinished)
                parts.append('</ul>')
            elif cid in checkins and checkins[cid]:
                parts.append('<p><small>No new work reported tonight. Older unfinished tasks, if any, would appear above.</small></p>')
            else:
                parts.append('<p><small>No unfinished tasks recorded.</small></p>')
            for task in tasks_by_class.get(cid,[]):
                tid=task["id"]
                choices=[a for a in linked_choices if a["class_id"]==cid]
                if task["linked_canvas_id"]:
                    parts.append(f'<p><small>Related Canvas assignment: {esc(task["linked_canvas_title"])} '
                                 '(the two records remain separate; family task dates and completion stay independent)</small></p>'
                                 + ('<p role="status">Canvas item not found in latest import. Family task preserved.</p>' if task["linked_canvas_missing"] else '')
                                 + (f'<p role="status">Date conflict: family {esc(friendly_date(task["due_date"]))}; Canvas {esc(friendly_date(task["linked_canvas_due_date"]))}. Family date takes precedence for this task.</p>' if task["due_date"] and task["linked_canvas_due_date"] and task["due_date"] != task["linked_canvas_due_date"] else '')
                                 + f'<form class="inline" method="post" action="/parent/entries/{tid}/canvas-unlink">'
                                 '<button class="secondary" type="submit">Remove Canvas link</button></form>')
                if choices:
                    parts.append(f'<form method="post" action="/parent/entries/{tid}/canvas-link">'
                                 '<label>Related Canvas assignment (optional)</label>'
                                 '<select name="canvas_assignment_id">')
                    parts.extend(f'<option value="{a["id"]}"'
                                 + (' selected' if a["id"]==task["linked_canvas_id"] else '')
                                 + f'>{esc(a["title"])}</option>' for a in choices)
                    parts.append('</select><button class="secondary" type="submit">Link Canvas assignment</button></form>')
                parts.append(f'<form class="inline" method="post" action="/parent/entries/{tid}/plan">'
                             f'<label for="plan-{tid}">Work date for {esc(task["details"])} (blank = show now)</label>'
                             f'<input id="plan-{tid}" type="date" name="planned_date" value="{esc(task["planned_date"] or "")}">'
                             '<button class="secondary" type="submit">Save work date</button></form>')
                if task["done"]:
                    state='Parent confirmed' if task["parent_confirmed"] else 'Student says done — review needed'
                    parts.append(f'<p><small>{esc(task["kind"])} — {esc(task["details"])}: {state}'
                                 + (f' · Completed {esc(task["completed_at"])} UTC' if task["completed_at"] else '')
                                 + '</small></p>')
                if task["done"] and not task["parent_confirmed"]:
                    parts.append(f'<form class="inline" method="post" action="/parent/entries/{tid}/confirm">'
                                 '<button type="submit">Confirm complete</button></form> '
                                 f'<form class="inline" method="post" action="/parent/entries/{tid}/return">'
                                 '<button class="secondary" type="submit">Needs another look</button></form>')
                if task["coaching_note"]:
                    parts.append(f'<p><small>Coaching note: {esc(task["coaching_note"])}</small></p>')
                parts.append(f'<form method="post" action="/parent/entries/{tid}/note">'
                             f'<label for="note-{tid}">Coaching note (optional)</label>'
                             f'<input id="note-{tid}" name="note" maxlength="300" value="{esc(task["coaching_note"])}">'
                             '<button class="secondary" type="submit">Save note</button></form>')
                parts.append(
                    f'<p><a href="/entries/{tid}/edit">Edit task</a> '
                    f'<form class="inline" method="post" action="/parent/entries/{tid}/delete" '
                    'onsubmit="return confirm(&quot;Delete this task permanently?&quot;);">'
                    '<button class="danger" type="submit">Delete task</button></form></p>'
                )
            parts.append('</div>')
        parts.append('</section>')
    if ask_teacher:
        parts.append('<section class="panel"><h3>Questions needing follow-up</h3>')
        for task in ask_teacher:
            cls_name=next((c["name"] for c in classes if c["id"]==task["class_id"]),"Unknown class")
            parts.append(f'<p><strong>{esc(cls_name)}</strong>: {esc(task["details"])}</p>')
        parts.append('</section>')
    if lunch_tasks:
        parts.append('<section class="panel"><h3>Lunch Buddies tasks and notes</h3>')
        for task in lunch_tasks:
            tid=task['id']
            state='Parent confirmed' if task['parent_confirmed'] else 'Student says done — review needed' if task['done'] else 'Not started'
            parts.append(f'<div class="class"><strong>{esc(task["activity_name"])}</strong>: '
                         f'{esc(task["details"])} · {state}</div>')
            if task['done'] and not task['parent_confirmed']:
                parts.append(f'<form class="inline" method="post" action="/parent/lunch-buddies/tasks/{tid}/confirm">'
                             '<button type="submit">Confirm complete</button></form> '
                             f'<form class="inline" method="post" action="/parent/lunch-buddies/tasks/{tid}/return">'
                             '<button class="secondary" type="submit">Needs another look</button></form>')
            parts.append(f'<form method="post" action="/parent/lunch-buddies/tasks/{tid}/note">'
                         f'<label>Coaching note</label><input name="note" maxlength="300" value="{esc(task["coaching_note"])}">'
                         '<button class="secondary" type="submit">Save note</button></form>')
            parts.append(f'<form method="post" action="/parent/lunch-buddies/tasks/{tid}/delete" '
                         'onsubmit="return confirm(&quot;Delete this task permanently?&quot;);">'
                         '<button class="danger" type="submit">Delete task</button></form>')
        parts.append('</section>')
    return layout("Parent Review","".join(parts))

@router.get("/settings",response_class=HTMLResponse)
def settings():
    with db() as conn:
        classes=get_active_classes(conn)
        expectations=conn.execute("""SELECT r.*,c.name AS class_name
            FROM recurring_expectations r JOIN classes c ON c.id=r.class_id
            ORDER BY c.sort_order,c.id,r.id""").fetchall()
    parts=['<section class="panel"><h3>Classes and school schedule</h3>',
           '<p>Set up courses, class periods, school-day exceptions, and activities.</p>',
           '<p><a href="/parent/classes">Manage Classes and Canvas course links</a></p>',
           '<p><a href="/parent/schedule">Bell Schedule</a></p>',
           '<p><a href="/parent/school-days">School Days</a></p>',
           '<p><a href="/parent/lunch-buddies">Lunch Buddies</a></p></section>',
           '<section class="panel"><h3>Coming in later steps</h3>',
           '<p>'
           'Notifications and account permissions will be added here. They are not active yet.</p></section>',
           '<section class="panel"><h3>Access and safety</h3>',
           '<p>This prototype does not yet enforce separate parent, student, or school staff accounts. '
           'Keep it local; do not expose it publicly or enter sensitive student information.</p></section>']
    parts.insert(0, sync_controls("/settings"))
    parts.append('<section class="panel"><h3>Recurring expectations</h3>'
                 '<p>Parent-configured practice or study appears automatically on the afternoon plan. '
                 'Each day gets a separate task so yesterday’s completion is preserved.</p>')
    if classes:
        parts.append('<form method="post" action="/settings/expectations/add">'
                     '<label>Class</label><select name="class_id">')
        parts.extend(f'<option value="{c["id"]}">{esc(c["name"])}</option>' for c in classes)
        parts.append('</select><label>Expectation</label>'
                     '<input name="details" required maxlength="300" placeholder="Practice math for 20 minutes">'
                     '<input type="hidden" name="kind" value="Study">'
                     '<label>Repeat</label><select name="frequency">'
                     '<option value="daily">Every day</option>'
                     '<option value="weekdays">Monday–Friday</option></select>'
                     '<p><button type="submit">Add expectation</button></p></form>')
    else:
        parts.append('<p>Add an active class before creating expectations.</p>')
    for item in expectations:
        parts.append(f'<div class="class"><strong>{esc(item["class_name"])}</strong> — '
                     f'{esc(item["details"])} ({esc(item["frequency"])}) '
                     f'{"Active" if item["enabled"] else "Paused"}'
                     f'<form method="post" action="/settings/expectations/{item["id"]}/toggle">'
                     f'<button type="submit">{"Pause" if item["enabled"] else "Resume"}</button>'
                     '</form></div>')
    parts.append('</section>')
    return layout("Settings","".join(parts))

@router.get("/entries/{entry_id}/edit",response_class=HTMLResponse)
def edit_page(entry_id: int):
    with db() as conn:
        entry=conn.execute("""SELECT e.id,e.kind,e.details,e.due_date FROM entries e
            JOIN classes c ON c.id=e.class_id WHERE e.id=? AND e.kind!='Nothing Tonight'
            AND c.enabled=1 AND c.archived=0""",(entry_id,)).fetchone()
    if entry is None: raise HTTPException(404,"Entry not found")
    form=(f'<section class="panel"><form method="post" action="/entries/{entry_id}/edit">'
          '<label>Task type</label><select name="kind">'
          f'{options(entry["kind"])}</select><label>Details</label>'
          f'<input type="text" name="details" required maxlength="300" value="{esc(entry["details"])}">'
          + deadline_fields(entry["due_date"])
          + '<button type="submit">Save changes</button> <a href="/parent">Cancel</a></form></section>')
    return layout("Edit task",form)
