"""Local HTML pages for the SyncCanvas family planner."""
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
ACTIVE_CLASSES = "SELECT id, name FROM classes WHERE enabled=1 AND archived=0 ORDER BY sort_order, id"

def esc(value):
    return html.escape(str(value), quote=True)

def layout(title, content):
    css = """
    body{font-family:system-ui,Arial,sans-serif;background:#f4f7fb;color:#18253b;margin:0}
    header{background:#193a63;color:white;padding:18px max(20px,calc((100vw - 940px)/2))}
    header nav{display:flex;flex-wrap:wrap;align-items:center;gap:10px 20px}
    header a{color:white}header a.parent-link{margin-left:auto}
    main{max-width:940px;margin:28px auto;padding:0 18px}
    .panel{background:white;border:1px solid #dce4ee;border-radius:12px;padding:20px;margin:16px 0}
    .class{border-top:1px solid #e1e8f0;padding:14px 0}
    .canvas-card{border:1px solid #dce4ee;border-radius:10px;padding:12px 14px;margin:10px 0;background:white}
    .canvas-meta,.row{display:flex;flex-wrap:wrap;align-items:center;gap:8px 12px;margin-top:6px;line-height:1.5}
    .canvas-open{display:inline-flex;align-items:center;min-height:44px;padding:8px 13px;border-radius:8px;background:#1659a2;color:white;font-weight:600;text-decoration:none}
    input,select,button{font:inherit;padding:10px;border-radius:7px;border:1px solid #9baec4}
    button{background:#1659a2;color:white;border:0;cursor:pointer}
    button.secondary{background:#e5edf7;color:#193a63}button.danger{background:#9f2936}
    label{display:block;margin:8px 0 4px}form.inline{display:inline}
    small{color:#52647b}.done{text-decoration:line-through;color:#64748b}
    a{color:#1659a2}.status{font-weight:600}.unchecked{color:#a34d00}.checked{color:#147044}
    input[type=text]{min-width:220px}@media(max-width:580px){input,select,button{max-width:100%}.row>*{flex:1 1 170px}}
    """
    return HTMLResponse(
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>{esc(title)} · SyncCanvas</title><style>{css}</style></head><body>'
        '<header><h1>SyncCanvas</h1><nav><a href="/">My Classes</a>'
        '<a href="/review">Course Check-Out</a><a href="/home">Homework Review</a>'
        '<a class="parent-link" href="/parent">Parent Page</a></nav></header>'
        f'<main><h2>{esc(title)}</h2>{content}'
        '<p><small>Local prototype only · No accounts or cloud sync yet · Do not publish online</small></p>'
        '</main></body></html>'
    )

def today():
    return date.today().isoformat()

def options(selected=""):
    return "".join(f'<option value="{esc(kind)}"{" selected" if kind == selected else ""}>{esc(kind)}</option>' for kind in KINDS)

def get_active_classes(conn):
    return conn.execute(ACTIVE_CLASSES).fetchall()

def get_canvas_assignments(conn):
    return conn.execute("""SELECT a.id,a.title,a.due_date,a.due_at,a.html_url,
        a.submission_types,a.completed,c.id AS class_id,c.name AS class_name,c.sort_order
        FROM canvas_assignments a JOIN canvas_course_links l ON l.canvas_course_id=a.canvas_course_id
        JOIN classes c ON c.id=l.class_id WHERE c.enabled=1 AND c.archived=0
        ORDER BY CASE WHEN a.due_date IS NULL OR a.due_date='' THEN 1 ELSE 0 END,
        a.due_date,a.due_at,a.title,a.id""").fetchall()

def canvas_due_label(assignment):
    due = assignment["due_date"]
    if not due: return "No due date"
    if due < today(): return f"Overdue · {due}"
    if due == today(): return "Due today"
    return f"Due {due}"

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

def canvas_assignment_html(assignment, *, show_class=False):
    url = str(assignment["html_url"] or "").strip()
    link = (f'<a class="canvas-open" href="{esc(url)}" target="_blank" rel="noopener noreferrer">Open in Canvas ↗</a>'
            if url.lower().startswith("https://") else "")
    prefix = f'<strong>{esc(assignment["class_name"])}</strong>: ' if show_class else ""
    status = "Completed" if assignment["completed"] else canvas_due_label(assignment)
    return (f'<div class="canvas-card"><strong>{prefix}{esc(assignment["title"])}</strong>'
            f'<div class="canvas-meta"><small>{esc(status)} · '
            f'{esc(submission_label(assignment["submission_types"]))}</small>{link}</div></div>')

def completed_canvas_history(assignments):
    cutoff = (date.today()-timedelta(days=7)).isoformat()
    return [a for a in assignments if a["completed"] and a["due_date"] and a["due_date"]>=cutoff]

def canvas_history_html(assignments):
    recent = completed_canvas_history(assignments)
    parts = [f'<details class="panel"><summary>Recently completed Canvas assignments ({len(recent)})</summary>',
             '<p><small>Last 7 days by assignment due date; completion dates are not available yet.</small></p>']
    if not recent: parts.append('<p>No completed Canvas assignments due in the last 7 days.</p>')
    else: parts.extend(canvas_assignment_html(a,show_class=True) for a in reversed(recent))
    return "".join(parts)+"</details>"

def manual_entries(conn):
    return conn.execute("""SELECT e.id,e.class_id,e.kind,e.details,e.done,e.parent_confirmed,
        e.coaching_note,c.name AS class_name FROM entries e JOIN classes c ON c.id=e.class_id
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
        canvas_assignments=get_canvas_assignments(conn)
        entries=manual_entries(conn)
        checkins=checkins_today(conn)
    by_class={}
    for entry in entries: by_class.setdefault(entry["class_id"],[]).append(entry)
    canvas_by_class={}
    for assignment in canvas_assignments:
        if not assignment["completed"]: canvas_by_class.setdefault(assignment["class_id"],[]).append(assignment)
    sync=present_sync_status(sync_coordinator.status())
    parts=['<section class="panel"><h3>School updates</h3>',
           f'<p><strong>{esc(sync.label)}</strong> — {esc(sync.message)}</p>']
    if sync.state not in (SyncState.NOT_CONFIGURED.value,SyncState.RUNNING.value):
        parts.append('<form method="post" action="/sync/run"><button type="submit">Check for updates</button></form>')
    parts.append('</section>')
    if sync.state==SyncState.RUNNING.value:
        parts.append('''<script>(function(){let failures=0;async function checkSync(){try{
            const response=await fetch('/api/sync/status',{cache:'no-store',headers:{'Accept':'application/json'}});
            if(!response.ok)throw Error('Status unavailable');const status=await response.json();failures=0;
            if(status.state!=='running'){window.location.reload();return;}
            }catch(error){failures++;if(failures>=5){window.location.reload();return;}}
            window.setTimeout(checkSync,1500);}window.setTimeout(checkSync,1500);}());</script>''')
    if not classes:
        parts.append('<section class="panel"><p>No active classes are available yet. Classes are managed from the Parent page.</p></section>')
    for cls in classes:
        cid=cls["id"]
        css="unchecked" if cid not in checkins else "checked"
        parts.append(f'<section class="panel"><h3>{esc(cls["name"])}</h3>'
                     f'<p class="status {css}">{checkin_label(cid,checkins)}</p>')
        if canvas_by_class.get(cid):
            parts.append('<h4>Canvas assignments to do</h4>')
            parts.extend(canvas_assignment_html(a) for a in canvas_by_class[cid])
        for item in by_class.get(cid,[]):
            status=' class="done"' if item["done"] else ''
            state='Parent confirmed' if item["parent_confirmed"] else 'Waiting for parent review' if item["done"] else 'Not Started'
            note=f'<p><small>Parent note: {esc(item["coaching_note"])}</small></p>' if item["coaching_note"] else ''
            parts.append(f'<div class="class"><span{status}><strong>{esc(item["kind"])}</strong> — '
                         f'{esc(item["details"])}</span> · {esc(state)}{note}</div>')
        parts.append(f'''<form method="post" action="/classes/{cid}/entries">
            <label for="kind-{cid}">What needs to happen?</label><select id="kind-{cid}" name="kind">{options()}</select>
            <label for="details-{cid}">What exactly? (required)</label>
            <input type="text" id="details-{cid}" name="details" required maxlength="300" placeholder="e.g. Questions 1–10">
            <button type="submit">Add task &amp; check in</button></form>
            <div class="row"><form class="inline" method="post" action="/classes/{cid}/nothing">
            <button class="secondary" type="submit">Nothing Tonight</button></form>
            <form class="inline" method="post" action="/classes/{cid}/checkin">
            <button class="secondary" type="submit">Checked — still deciding</button></form></div></section>''')
    parts.append(canvas_history_html(canvas_assignments))
    return layout("My Classes","".join(parts))

@router.get("/review",response_class=HTMLResponse)
def review():
    with db() as conn:
        classes=get_active_classes(conn)
        checked=checkins_today(conn)
    parts=[f'<section class="panel"><p>Before leaving school, check every class for today ({esc(today())}). '
           'Make sure you have what you need to bring home.</p>']
    for cls in classes:
        parts.append(f'<div class="class"><strong>{esc(cls["name"])}</strong> — '
                     f'{esc(checkin_label(cls["id"],checked))} <a href="/">Open class</a></div>')
    return layout("Course Check-Out","".join(parts)+"</section>")

@router.get("/home",response_class=HTMLResponse)
def home():
    with db() as conn:
        canvas_assignments=get_canvas_assignments(conn)
        entries=[e for e in manual_entries(conn) if not e["done"]]
    parts=['<section class="panel"><h3>Canvas assignments to do</h3>',
           '<p>All incomplete assignments, including overdue work, sorted by due date.</p>']
    incomplete=[a for a in canvas_assignments if not a["completed"]]
    if not incomplete: parts.append('<p>No incomplete Canvas assignments.</p>')
    parts.extend(canvas_assignment_html(a,show_class=True) for a in incomplete)
    parts.append('</section>')
    parts.append(canvas_history_html(canvas_assignments))
    parts.extend(['<section class="panel"><h3>My added tasks</h3>',
                  '<p>Tasks still open, including tasks from previous days.</p>'])
    if not entries: parts.append('<p>No open tasks recorded.</p>')
    for item in entries:
        parts.append(f'<div class="class"><strong>{esc(item["class_name"])}</strong>: '
                     f'{esc(item["kind"])} — {esc(item["details"])} '
                     f'<form class="inline" method="post" action="/entries/{item["id"]}/done">'
                     '<button type="submit">Done</button></form></div>')
    return layout("Homework Review","".join(parts)+"</section>")

@router.get("/parent",response_class=HTMLResponse)
def parent():
    with db() as conn:
        classes=get_active_classes(conn)
        checkins=checkins_today(conn)
        tasks=manual_entries(conn)
    tasks_by_class={}
    for task in tasks: tasks_by_class.setdefault(task["class_id"],[]).append(task)
    checked_count=sum(c["id"] in checkins for c in classes)
    open_count=sum(not t["done"] for t in tasks)
    awaiting_count=sum(t["done"] and not t["parent_confirmed"] for t in tasks)
    missing=[c for c in classes if c["id"] not in checkins]
    ask_teacher=[t for t in tasks if t["kind"]=="Ask Teacher" and not t["done"]]
    parts=['<section class="panel"><h3>Class administration</h3>',
           '<p>Search Canvas, link courses, and manage enabled, disabled, or archived classes.</p>',
           '<p><a href="/parent/classes">Manage Classes</a></p></section>',
           '<section class="panel"><h3>Afternoon review</h3>',
           f'<p><strong>{checked_count}/{len(classes)}</strong> classes checked today · '
           f'<strong>{open_count}</strong> unfinished tasks · '
           f'<strong>{awaiting_count}</strong> awaiting parent confirmation · '
           f'<strong>{len(missing)+len(ask_teacher)}</strong> attention items</p>',
           '<p><small>Class check-ins apply to today; unfinished tasks can be from earlier days. '
           'Archived and disabled classes are excluded from the daily review.</small></p></section>']
    if not classes:
        parts.append('<section class="panel"><p>No active classes yet. <a href="/parent/classes">Manage Classes</a> to add or enable classes.</p></section>')
    else:
        parts.append('<section class="panel"><h3>All classes</h3>')
        for cls in missing+[c for c in classes if c["id"] in checkins]:
            cid=cls["id"]
            css="unchecked" if cid not in checkins else "checked"
            parts.append(f'<div class="class"><strong>{esc(cls["name"])}</strong> — '
                         f'<span class="status {css}">{esc(checkin_label(cid,checkins))}</span>')
            unfinished=[t for t in tasks_by_class.get(cid,[]) if not t["done"]]
            if unfinished:
                parts.append('<ul>')
                parts.extend(f'<li>{esc(t["kind"])} — {esc(t["details"])}</li>' for t in unfinished)
                parts.append('</ul>')
            elif cid in checkins and checkins[cid]:
                parts.append('<p><small>No new work reported tonight. Older unfinished tasks, if any, would appear above.</small></p>')
            else:
                parts.append('<p><small>No unfinished tasks recorded.</small></p>')
            for task in tasks_by_class.get(cid,[]):
                tid=task["id"]
                if task["done"]:
                    state='Parent confirmed' if task["parent_confirmed"] else 'Student says done — review needed'
                    parts.append(f'<p><small>{esc(task["kind"])} — {esc(task["details"])}: {state}</small></p>')
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
                parts.append(f'<p><a href="/entries/{tid}/edit">Edit task</a> '
                             f'<form class="inline" method="post" action="/parent/entries/{tid}/delete" '
                             'onsubmit="return confirm(\'Delete this task permanently?\');">'
                             '<button class="danger" type="submit">Delete task</button></form></p>')
            parts.append('</div>')
        parts.append('</section>')
    if ask_teacher:
        parts.append('<section class="panel"><h3>Questions needing follow-up</h3>')
        for task in ask_teacher:
            cls_name=next((c["name"] for c in classes if c["id"]==task["class_id"]),"Unknown class")
            parts.append(f'<p><strong>{esc(cls_name)}</strong>: {esc(task["details"])}</p>')
        parts.append('</section>')
    return layout("Parent Page","".join(parts))

@router.get("/entries/{entry_id}/edit",response_class=HTMLResponse)
def edit_page(entry_id: int):
    with db() as conn:
        entry=conn.execute("""SELECT e.id,e.kind,e.details FROM entries e
            JOIN classes c ON c.id=e.class_id WHERE e.id=? AND e.kind!='Nothing Tonight'
            AND c.enabled=1 AND c.archived=0""",(entry_id,)).fetchone()
    if entry is None: raise HTTPException(404,"Entry not found")
    form=(f'<section class="panel"><form method="post" action="/entries/{entry_id}/edit">'
          '<label>Task type</label><select name="kind">'
          f'{options(entry["kind"])}</select><label>Details</label>'
          f'<input type="text" name="details" required maxlength="300" value="{esc(entry["details"])}">'
          '<button type="submit">Save changes</button> <a href="/parent">Cancel</a></form></section>')
    return layout("Edit task",form)
