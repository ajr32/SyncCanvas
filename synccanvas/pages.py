
"""Local HTML pages for the SyncCanvas family planner."""
import html
import json
import secrets
import sqlite3
from datetime import date, datetime, timedelta
from fastapi import APIRouter, HTTPException
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
    main{max-width:940px;margin:28px auto;padding:0 18px}
    .panel{background:white;border:1px solid #dce4ee;border-radius:12px;padding:20px;margin:16px 0}
    .class{border-top:1px solid #e1e8f0;padding:14px 0}
    .task-group{display:grid;gap:12px}.task-card{border:1px solid #dce4ee;border-radius:10px;padding:16px;background:#fff}.task-card h4{margin:0 0 6px}.task-card p{margin:6px 0}.task-top{display:flex;justify-content:space-between;align-items:start;gap:12px;flex-wrap:wrap}.task-source{font-size:.82rem;font-weight:700;color:#52647b}.task-progress{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.task-progress select{min-width:145px}.muted{color:#52647b}.summary-grid{display:flex;gap:12px;flex-wrap:wrap}.summary-grid span{background:#edf3fb;border-radius:8px;padding:10px 14px}.canvas-card{border:1px solid #dce4ee;border-radius:10px;padding:12px 14px;margin:10px 0;background:white}
    .linked-work{border-top:1px solid #dce4ee;margin-top:14px;padding-top:12px}.linked-work h5{font-size:1rem;margin:0 0 6px}.linked-child{background:#f7faff;margin:10px 0 0 16px;border-left:4px solid #7598c7}.linked-child .task-class{font-size:1rem}
    .task-class{display:block;font-size:1.18rem;font-weight:750;line-height:1.35;color:#193a63;margin-bottom:3px}
    .task-origin{display:block;font-size:.76rem;font-weight:500;letter-spacing:.03em;color:#64748b;margin-bottom:7px}
    .due-overdue{color:#b42332!important;font-weight:750}
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
        '<header><h1>SyncCanvas</h1><nav><a href="/afternoon">My Afternoon</a>'
        '<a href="/add">Add Information</a><a href="/review">School Check-Out</a>'
        '<a class="parent-link" href="/parent">Parent Review</a>'
        '<a href="/settings">Settings</a></nav></header>'
        f'<main><h2>{esc(title)}</h2>{content}'
        '<p><small>Local prototype only · No accounts or cloud sync yet · Do not publish online</small></p>'
        '''<script>
        document.addEventListener('DOMContentLoaded', function () {
          const status = document.createElement('p');
          status.setAttribute('role', 'status');
          status.setAttribute('aria-live', 'polite');
          status.style.cssText = 'position:sticky;bottom:0;background:#edf3fb;padding:8px;border-radius:8px;display:none';
          document.querySelector('main').appendChild(status);
          document.querySelectorAll('form[method="post"]').forEach(function (form) {
            form.addEventListener('submit', function () {
              if (form.dataset.submitting === 'yes') return;
              form.dataset.submitting = 'yes';
              status.textContent = 'Saving or loading… Please wait.';
              status.style.display = 'block';
              form.querySelectorAll('button[type="submit"],button:not([type])').forEach(function (button) {
                button.disabled = true;
                button.textContent = 'Working…';
              });
            });
          });
          window.addEventListener('pageshow', function (event) {
            if (event.persisted) window.location.reload();
          });
        });
        </script></main></body></html>'''
    )

def today():
    return date.today().isoformat()

def options(selected=""):
    return "".join(f'<option value="{esc(kind)}"{" selected" if kind == selected else ""}>{esc(kind)}</option>' for kind in KINDS)

def get_active_classes(conn):
    weekday = str(date.today().weekday())
    day = date.today().isoformat()
    try:
        exception = conn.execute('SELECT kind FROM school_days WHERE day=?', (day,)).fetchone()
        if exception and exception['kind']=='closed':
            return conn.execute("SELECT id,name,NULL AS period_label,NULL AS period_start FROM classes WHERE enabled=1 AND archived=0 ORDER BY sort_order,id").fetchall()
    except sqlite3.OperationalError as exc:
        if 'no such table' not in str(exc): raise
    try:
        return conn.execute("""
        SELECT c.id, c.name,
            (SELECT p.label FROM class_periods cp JOIN bell_periods p
             ON p.id=cp.period_id WHERE cp.class_id=c.id
             AND instr(p.weekdays, ?) > 0
             ORDER BY p.start_time, p.id LIMIT 1) AS period_label,
            (SELECT COALESCE((SELECT sp.start_time FROM school_day_periods sp WHERE sp.period_id=p.id AND sp.day=?),p.start_time) FROM class_periods cp JOIN bell_periods p
             ON p.id=cp.period_id WHERE cp.class_id=c.id
             AND instr(p.weekdays, ?) > 0
             ORDER BY COALESCE((SELECT sp.start_time FROM school_day_periods sp WHERE sp.period_id=p.id AND sp.day=?),p.start_time), p.id LIMIT 1) AS period_start
        FROM classes c WHERE c.enabled=1 AND c.archived=0
        ORDER BY CASE WHEN (SELECT 1 FROM class_periods cp JOIN bell_periods p ON p.id=cp.period_id WHERE cp.class_id=c.id AND instr(p.weekdays, ?) > 0 LIMIT 1) IS NULL THEN 1 ELSE 0 END,
                 period_start, c.sort_order, c.id
    """, (weekday, day, weekday, day, weekday)).fetchall()
    except sqlite3.OperationalError as exc:
        if "no such table" not in str(exc):
            raise
        return conn.execute("SELECT id,name,NULL AS period_label,NULL AS period_start FROM classes WHERE enabled=1 AND archived=0 ORDER BY sort_order,id").fetchall()

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
    if due < today(): return f"Overdue · {friendly_date(due)}"
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

def canvas_assignment_html(assignment, *, show_class=False):
    url = str(assignment["html_url"] or "").strip()
    link = (f'<a class="canvas-open" href="{esc(url)}" target="_blank" rel="noopener noreferrer">Open in Canvas ↗</a>'
            if url.lower().startswith("https://") else "")
    prefix = f'<span class="task-class">{esc(assignment["class_name"])}</span>' if show_class else ""
    status = "Completed" if assignment["completed"] else canvas_due_label(assignment)
    due_class = "due-overdue" if not assignment["completed"] and status.startswith("Overdue") else ""
    return (f'<div class="canvas-card">{prefix}<strong>{esc(assignment["title"])}</strong>'
            f'<div class="canvas-meta"><small><span class="{due_class}">{esc(status)}</span> · '
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
    columns={r["name"] for r in conn.execute("PRAGMA table_info(entries)")}
    origin="e.origin" if "origin" in columns else "'student' AS origin"
    planned="e.planned_date" if "planned_date" in columns else "NULL AS planned_date"
    linked=conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='entry_canvas_links'").fetchone()
    canvas=conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='canvas_assignments'").fetchone()
    if linked and canvas:
        relation="LEFT JOIN entry_canvas_links link ON link.entry_id=e.id LEFT JOIN canvas_assignments a ON a.id=link.canvas_assignment_id"
        linked_columns="a.title AS linked_canvas_title, a.id AS linked_canvas_id"
    else:
        relation=""
        linked_columns="NULL AS linked_canvas_title, NULL AS linked_canvas_id"
    return conn.execute(f"""SELECT e.id,e.class_id,e.kind,e.details,e.done,e.parent_confirmed,
        e.coaching_note,e.progress,e.completed_at,{origin},{planned},c.name AS class_name,
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
                (today(),today(),str(date.today().weekday()),str(date.today().weekday()))).fetchall()
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
            <input type="hidden" name="submission_token" value="{secrets.token_hex(32)}">
            <button type="submit">Add task &amp; check in</button></form>
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
        parts.append('<form id="quick-entry" method="post">'
                     '<label for="quick-class">Class</label><select id="quick-class" required>')
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
                     f'<input type="hidden" name="submission_token" value="{secrets.token_hex(32)}">'
                     '<p><button type="submit">Save</button></p></form>'
                     '<script>(function(){const form=document.getElementById("quick-entry");'
                     'const field=document.getElementById("quick-class");'
                     'function update(){form.action="/classes/"+field.value+"/entries";}'
                     'field.addEventListener("change",update);update();})();</script>')
    parts.append('<p><a href="/">Detailed class check-in</a></p></section>')
    return layout("Add Information","".join(parts))


@router.get("/review",response_class=HTMLResponse)
def review():
    with db() as conn:
        classes=get_active_classes(conn)
        checked=checkins_today(conn)
        entries=manual_entries(conn)
        assignments=get_canvas_assignments(conn)
        school_reviews={r["class_id"]:r["outcome"] for r in conn.execute(
            "SELECT class_id,outcome FROM school_reviews WHERE day=?",(today(),))}
        questions={r["class_id"]:r for r in conn.execute(
            "SELECT class_id,question,resolved FROM class_questions WHERE day=?",(today(),))}
        paper=conn.execute("SELECT * FROM paper_reviews WHERE day=?",(today(),)).fetchone()
    by_class={}
    for entry in entries:
        by_class.setdefault(entry["class_id"],[]).append(entry)
    canvas_by_class={}
    for assignment in assignments:
        if not assignment["completed"]:
            canvas_by_class.setdefault(assignment["class_id"],[]).append(assignment)
    completed=sum(c["id"] in school_reviews for c in classes)
    parts=['<section class="panel"><h3>School check-out</h3>',
           f'<p><strong>{completed} of {len(classes)}</strong> classes reviewed today.</p>',
           '<p>Check every class with the school aide. These are locally saved review records, '
           'not authenticated staff signatures. Student check-ins are shown separately.</p></section>']
    for cls in classes:
        cid=cls["id"]
        outcome=school_reviews.get(cid)
        status={'reviewed':'Reviewed','nothing':'Reviewed — nothing needed',
                'needs_followup':'Reviewed — follow-up needed'}.get(outcome,'Not reviewed')
        parts.append(f'<section class="panel"><h3 class="task-class">{esc(cls["name"])}</h3>'
                     f'<p>School review: <strong>{esc(status)}</strong> · Student: '
                     f'{esc(checkin_label(cid,checked))}</p>')
        canvas=canvas_by_class.get(cid,[])
        current=by_class.get(cid,[])
        if canvas:
            parts.append('<h4>Canvas context (read-only)</h4>')
            parts.extend(canvas_assignment_html(a) for a in canvas)
        if current:
            parts.append('<h4>Student and parent notes</h4><ul>')
            parts.extend(f'<li>{esc(e["kind"])} — {esc(e["details"])}</li>' for e in current)
            parts.append('</ul>')
        if not canvas and not current:
            parts.append('<p>No work recorded. Ask about this class before confirming.</p>')
        parts.append('<p><a href="/add">+ Add missing information</a></p>'
                     f'<form method="post" action="/school/classes/{cid}/review">'
                     '<label>Review result</label><select name="outcome">'
                     '<option value="reviewed">Reviewed — work checked</option>'
                     '<option value="nothing">Reviewed — nothing needed</option>'
                     '<option value="needs_followup">Reviewed — needs follow-up</option>'
                     '</select> <button type="submit">Save class review</button></form>')
        question=questions.get(cid)
        parts.append(f'<form method="post" action="/school/classes/{cid}/question">'
                     '<label>Missing or unclear information (optional)</label>'
                     f'<input type="text" name="question" maxlength="300" value="{esc(question["question"] if question else "")}" '
                     'placeholder="e.g. Ask whether worksheet is homework">'
                     f'<label><input type="checkbox" name="resolved" value="yes" {"checked" if question and question["resolved"] else ""}> Resolved</label>'
                     '<button class="secondary" type="submit">Save question</button></form></section>')
    parts.append('<section class="panel"><h3>Physical papers</h3>'
                 '<p>Check the accordion pocket at the front of the binder and look in the backpack '
                 'for loose papers. No need to inventory every worksheet.</p>'
                 '<form method="post" action="/school/papers">'
                 f'<label><input type="checkbox" name="pocket_checked" value="yes" {"checked" if paper and paper["pocket_checked"] else ""}> Accordion pocket checked</label>'
                 f'<label><input type="checkbox" name="backpack_checked" value="yes" {"checked" if paper and paper["backpack_checked"] else ""}> Backpack checked</label>'
                 '<label>Paper note (optional)</label>'
                 f'<input type="text" name="notes" maxlength="300" value="{esc(paper["notes"] if paper else "")}">'
                 '<p><button type="submit">Save paper check</button></p></form>'
                 '<p><small>Saved locally without staff identity verification.</small></p></section>')
    return layout("School Check-Out","".join(parts))

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
    incomplete=[a for a in canvas_assignments if not a["completed"]]
    open_entries=[e for e in entries if not e["done"] and (not e["planned_date"] or e["planned_date"] <= today())]
    waiting=[e for e in entries if e["done"] and not e["parent_confirmed"]]
    upcoming=[e for e in entries if not e["done"] and e["planned_date"] and e["planned_date"] > today()]
    parts=['<section class="panel"><h3>Today’s plan</h3>',
           '<p>Canvas work, classroom reminders, and other unfinished tasks in one place. '
           'Canvas due dates are the official deadlines; a completed Canvas submission may still need review.</p>',
           '<div class="summary-grid">',
           f'<span><strong>{len(incomplete)}</strong> Canvas to do</span>',
           f'<span><strong>{len(open_entries)}</strong> Added tasks open</span>',
           f'<span><strong>{len(waiting)}</strong> Waiting for parent</span>',
           '</div><p><a href="/add">+ Add something I still need to do</a></p></section>',
           '<section class="panel"><h3>Work to do</h3><div class="task-group">']
    if not incomplete and not open_entries and not lunch_open:
        parts.append('<p>No unfinished work is recorded. Check with an adult before assuming there is nothing else.</p>')
    # Display related Canvas and manual work together without merging their records.
    linked_open = {}
    for entry in open_entries:
        if entry["linked_canvas_id"] is not None:
            linked_open.setdefault(entry["linked_canvas_id"], []).append(entry)
    rendered_entry_ids = set()

    def manual_task_card(item, *, nested=False):
        state = item["progress"] or "not_started"
        origin = "Parent added" if item["origin"] == "parent" else "Added information"
        card_class = "task-card linked-child" if nested else "task-card"
        related = (f'<p class="muted">Related Canvas: {esc(item["linked_canvas_title"])}</p>'
                   if item["linked_canvas_title"] and not nested else "")
        return (f'<article class="{card_class}"><span class="task-class">{esc(item["class_name"])}</span>'
                f'<span class="task-origin">{origin}</span><h4>{esc(item["details"])}</h4>'
                f'<p class="muted">{esc(item["kind"])}</p>{related}'
                f'<form class="task-progress" method="post" action="/entries/{item["id"]}/progress">'
                f'<label for="progress-{item["id"]}">Progress</label>'
                f'<select id="progress-{item["id"]}" name="progress">'
                f'<option value="not_started"{" selected" if state=="not_started" else ""}>Not started</option>'
                f'<option value="in_progress"{" selected" if state=="in_progress" else ""}>In progress</option>'
                '<option value="done">Done</option></select>'
                '<button type="submit">Save progress</button></form>'
                + (f'<p><small>Parent note: {esc(item["coaching_note"])}</small></p>'
                   if item["coaching_note"] else '') + '</article>')

    for item in incomplete:
        url = str(item["html_url"] or "").strip()
        link = (f'<a class="canvas-open" href="{esc(url)}" target="_blank" rel="noopener noreferrer">Open in Canvas ↗</a>'
                if url.lower().startswith("https://") else "")
        due_label = canvas_due_label(item)
        due_class = "due-overdue" if due_label.startswith("Overdue") else ""
        children = linked_open.get(item["id"], [])
        parts.append(f'<article class="task-card"><div class="task-top"><div>'
                     f'<span class="task-class">{esc(item["class_name"])}</span>'
                     '<span class="task-origin">Canvas assignment · Official details</span>'
                     f'<h4>{esc(item["title"])}</h4><p class="muted"><span class="{due_class}">{esc(due_label)}</span> · '
                     f'{esc(submission_label(item["submission_types"]))}</p></div>{link}</div>')
        if children:
            parts.append(f'<div class="linked-work"><h5>Related Canvas: {esc(item["title"])} · Notes and tasks ({len(children)})</h5>'
                         '<p class="muted"><small>Canvas and added tasks keep separate progress and deadlines.</small></p>')
            for entry in children:
                parts.append(manual_task_card(entry, nested=True))
                rendered_entry_ids.add(entry["id"])
            parts.append('</div>')
        parts.append('</article>')
    for item in open_entries:
        if item["id"] not in rendered_entry_ids:
            parts.append(manual_task_card(item))
    for task in lunch_open:
        parts.append(f'<article class="task-card"><span class="task-class">{esc(task["activity_name"])}</span><span class="task-origin">Lunch Buddies</span>'
                     f'<h4>{esc(task["details"])}</h4>'
                     f'<form method="post" action="/parent/lunch-buddies/tasks/{task["id"]}/done">'
                     '<button type="submit">Done</button></form></article>')
    parts.append('</div></section>')
    if upcoming:
        parts.append(f'<details class="panel"><summary>Planned for later ({len(upcoming)})</summary>'
                     '<p><small>These tasks are saved, but their planned work dates have not arrived. '
                     'Canvas official deadlines are not changed.</small></p>')
        for item in sorted(upcoming,key=lambda entry:(entry["planned_date"],entry["class_name"])):
            parts.append(f'<div class="class"><strong>{esc(item["class_name"])}</strong> · '
                         f'{esc(item["details"])} · Work on {esc(friendly_date(item["planned_date"]))}</div>')
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
                     '<label for="parent-date">Work on (optional)</label>'
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
                parts.extend(f'<li>{esc(t["kind"])} — {esc(t["details"])}</li>' for t in unfinished)
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
                                 '(the two records remain separate)</small></p>'
                                 f'<form class="inline" method="post" action="/parent/entries/{tid}/canvas-unlink">'
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
