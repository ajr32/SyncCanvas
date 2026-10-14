"""SyncCanvas local-only prototype. Do not expose publicly without authentication."""
from __future__ import annotations

import html
import os
import sqlite3
from contextlib import contextmanager
from datetime import date
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse

DB_PATH = Path(os.environ.get("SYNCCANVAS_DB", "synccanvas_local.sqlite3"))
KINDS = ("Homework", "Study", "Finish Classwork", "Prepare for Quiz", "Ask Teacher")
app = FastAPI(title="SyncCanvas (local prototype)")


@contextmanager
def db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS classes (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, sort_order INTEGER NOT NULL DEFAULT 0)")
        conn.execute("CREATE TABLE IF NOT EXISTS entries (id INTEGER PRIMARY KEY, class_id INTEGER NOT NULL REFERENCES classes(id), kind TEXT NOT NULL, details TEXT NOT NULL DEFAULT '', done INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
        conn.execute("CREATE TABLE IF NOT EXISTS checkins (class_id INTEGER NOT NULL REFERENCES classes(id), day TEXT NOT NULL, nothing_tonight INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(class_id, day))")
        conn.commit()
        yield conn
        conn.commit()
    finally:
        conn.close()


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def go(path: str = "/") -> RedirectResponse:
    return RedirectResponse(path, status_code=303)


def layout(title: str, content: str) -> HTMLResponse:
    css = """body{font-family:system-ui,Arial,sans-serif;background:#f4f7fb;color:#18253b;margin:0}header{background:#193a63;color:white;padding:18px max(20px,calc((100vw - 940px)/2))}header a{color:white;margin-right:20px}main{max-width:940px;margin:28px auto;padding:0 18px}.panel{background:white;border:1px solid #dce4ee;border-radius:12px;padding:20px;margin:16px 0}.class{border-top:1px solid #e1e8f0;padding:14px 0}input,select,button{font:inherit;padding:10px;border-radius:7px;border:1px solid #9baec4}button{background:#1659a2;color:white;border:0;cursor:pointer}button.secondary{background:#e5edf7;color:#193a63}label{display:block;margin:8px 0 4px}form.inline{display:inline}small{color:#52647b}.done{text-decoration:line-through;color:#64748b}.row{display:flex;flex-wrap:wrap;align-items:center;gap:10px}a{color:#1659a2}.status{font-weight:600}.unchecked{color:#a34d00}.checked{color:#147044}input[type=text]{min-width:220px}@media(max-width:580px){input,select,button{max-width:100%}.row>*{flex:1 1 170px}}"""
    return HTMLResponse(f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)} · SyncCanvas</title><style>{css}</style></head><body><header><h1>SyncCanvas</h1><nav><a href="/">Classes</a><a href="/review">Before leaving</a><a href="/home">At home</a><a href="/parent">Parent preview</a></nav></header><main><h2>{esc(title)}</h2>{content}<p><small>Local prototype only · No accounts or cloud sync yet · Do not publish online</small></p></main></body></html>')


def today() -> str:
    return date.today().isoformat()


def set_checkin(conn, class_id: int, nothing: bool = False):
    conn.execute("INSERT INTO checkins(class_id,day,nothing_tonight) VALUES (?,?,?) ON CONFLICT(class_id,day) DO UPDATE SET nothing_tonight=excluded.nothing_tonight", (class_id, today(), int(nothing)))


def require_class(conn, class_id: int):
    if not conn.execute("SELECT 1 FROM classes WHERE id=?", (class_id,)).fetchone():
        raise HTTPException(404, "Class not found")


def options(selected: str = "") -> str:
    return ''.join(f'<option value="{esc(k)}"{" selected" if k == selected else ""}>{esc(k)}</option>' for k in KINDS)


@app.get("/", response_class=HTMLResponse)
def student():
    with db() as conn:
        classes = conn.execute("SELECT id,name FROM classes ORDER BY sort_order,id").fetchall()
        entries = conn.execute("SELECT id,class_id,kind,details,done FROM entries WHERE kind != 'Nothing Tonight' ORDER BY id DESC").fetchall()
        checkins = {r['class_id']: r['nothing_tonight'] for r in conn.execute("SELECT class_id,nothing_tonight FROM checkins WHERE day=?", (today(),))}
    by_class = {}
    for entry in entries:
        by_class.setdefault(entry['class_id'], []).append(entry)
    parts = ['<section class="panel"><h3>Add a class</h3><form method="post" action="/classes"><label for="name">Class name</label><div class="row"><input id="name" name="name" required maxlength="80" placeholder="e.g. Mathematics 7"><button>Add class</button></div></form></section>']
    if not classes:
        parts.append('<section class="panel">Add your first class to begin.</section>')
    for cls in classes:
        cid = cls['id']
        state = ('Not checked yet' if cid not in checkins else 'Nothing tonight' if checkins[cid] else 'Checked today')
        css_class = 'unchecked' if cid not in checkins else 'checked'
        parts.append(f'<section class="panel"><h3>{esc(cls["name"])}</h3><p class="status {css_class}">{state}</p>')
        for item in by_class.get(cid, []):
            status = ' class="done"' if item['done'] else ''
            detail = f' — {esc(item["details"])}' if item['details'] else ''
            parts.append(f'<div class="class"><span{status}><strong>{esc(item["kind"])}</strong>{detail}</span> <form class="inline" method="post" action="/entries/{item["id"]}/toggle"><button type="submit">{"Undo" if item["done"] else "Done"}</button></form> <a href="/entries/{item["id"]}/edit">Edit</a></div>')
        parts.append(f'<form method="post" action="/classes/{cid}/entries"><label for="kind-{cid}">What needs to happen?</label><select id="kind-{cid}" name="kind">{options()}</select><label for="details-{cid}">What exactly? (required)</label><input type="text" id="details-{cid}" name="details" required maxlength="300" placeholder="e.g. Questions 1–10"><button type="submit">Add task & check in</button></form>')
        parts.append(f'<p><form class="inline" method="post" action="/classes/{cid}/nothing"><button class="secondary" type="submit">Nothing Tonight</button></form> <form class="inline" method="post" action="/classes/{cid}/checkin"><button class="secondary" type="submit">Checked — still deciding</button></form></p></section>')
    return layout("My classes", ''.join(parts))


@app.get("/review", response_class=HTMLResponse)
def review():
    with db() as conn:
        classes = conn.execute("SELECT id,name FROM classes ORDER BY sort_order,id").fetchall()
        checked = {r['class_id']: r['nothing_tonight'] for r in conn.execute("SELECT class_id,nothing_tonight FROM checkins WHERE day=?", (today(),))}
    parts = [f'<section class="panel"><p>Before leaving school, check every class for today ({esc(today())}). Make sure you have what you need to bring home.</p>']
    for cls in classes:
        state = 'Not checked yet' if cls['id'] not in checked else 'Nothing tonight' if checked[cls['id']] else 'Checked today'
        parts.append(f'<div class="class"><strong>{esc(cls["name"])}</strong> — {esc(state)} <a href="/">Open class</a></div>')
    parts.append('</section>')
    return layout("Before leaving school", ''.join(parts))


@app.get("/home", response_class=HTMLResponse)
def home():
    with db() as conn:
        entries = conn.execute("SELECT c.name,e.id,e.kind,e.details,e.done FROM entries e JOIN classes c ON c.id=e.class_id WHERE e.kind != 'Nothing Tonight' AND e.done=0 ORDER BY c.sort_order,c.id,e.id").fetchall()
    parts = ['<section class="panel"><p>Tasks still open, including tasks from previous days.</p>']
    if not entries:
        parts.append('<p>No open tasks recorded.</p>')
    for item in entries:
        parts.append(f'<div class="class"><strong>{esc(item["name"])}</strong>: {esc(item["kind"])} — {esc(item["details"])} <form class="inline" method="post" action="/entries/{item["id"]}/toggle"><button>Done</button></form></div>')
    parts.append('</section>')
    return layout("At home", ''.join(parts))


@app.get("/parent", response_class=HTMLResponse)
def parent():
    with db() as conn:
        rows = conn.execute("SELECT c.name,e.kind,e.details,e.done FROM entries e JOIN classes c ON c.id=e.class_id WHERE e.kind != 'Nothing Tonight' ORDER BY c.sort_order,c.id,e.id DESC").fetchall()
    parts = ['<section class="panel"><p>Read-only preview. Parent authentication and verification will come later.</p>']
    if not rows:
        parts.append('<p>No tasks yet.</p>')
    for row in rows:
        parts.append(f'<div class="class"><strong>{esc(row["name"])}</strong>: {esc(row["kind"])} {esc(row["details"])} — {"Done" if row["done"] else "Open"}</div>')
    parts.append('</section>')
    return layout("Parent overview", ''.join(parts))


@app.post("/classes")
def add_class(name: str = Form(...)):
    name = name.strip()
    if not 1 <= len(name) <= 80:
        raise HTTPException(422, "Class name must be 1–80 characters")
    with db() as conn:
        conn.execute("INSERT OR IGNORE INTO classes(name) VALUES (?)", (name,))
    return go()


@app.post("/classes/{class_id}/entries")
def add_entry(class_id: int, kind: str = Form(...), details: str = Form(...)):
    details = details.strip()
    if kind not in KINDS or not details or len(details) > 300:
        raise HTTPException(422, "Choose a task type and enter a description (1–300 characters)")
    with db() as conn:
        require_class(conn, class_id)
        conn.execute("INSERT INTO entries(class_id,kind,details) VALUES (?,?,?)", (class_id, kind, details))
        set_checkin(conn, class_id)
    return go()


@app.post("/classes/{class_id}/nothing")
def nothing_tonight(class_id: int):
    with db() as conn:
        require_class(conn, class_id)
        # Do not erase existing tasks; simply record today's explicit check-in.
        set_checkin(conn, class_id, nothing=True)
    return go()


@app.post("/classes/{class_id}/checkin")
def checked_today(class_id: int):
    with db() as conn:
        require_class(conn, class_id)
        set_checkin(conn, class_id)
    return go()


@app.get("/entries/{entry_id}/edit", response_class=HTMLResponse)
def edit_page(entry_id: int):
    with db() as conn:
        entry = conn.execute("SELECT id,kind,details FROM entries WHERE id=? AND kind != 'Nothing Tonight'", (entry_id,)).fetchone()
    if entry is None:
        raise HTTPException(404, "Entry not found")
    form = f'<section class="panel"><form method="post" action="/entries/{entry_id}/edit"><label>Task type</label><select name="kind">{options(entry["kind"])}</select><label>Details</label><input type="text" name="details" required maxlength="300" value="{esc(entry["details"])}"><button>Save changes</button> <a href="/">Cancel</a></form></section>'
    return layout("Edit task", form)


@app.post("/entries/{entry_id}/edit")
def edit_entry(entry_id: int, kind: str = Form(...), details: str = Form(...)):
    details = details.strip()
    if kind not in KINDS or not details or len(details) > 300:
        raise HTTPException(422, "Invalid task")
    with db() as conn:
        result = conn.execute("UPDATE entries SET kind=?,details=? WHERE id=? AND kind != 'Nothing Tonight'", (kind, details, entry_id))
        if result.rowcount == 0:
            raise HTTPException(404, "Entry not found")
    return go()


@app.post("/entries/{entry_id}/toggle")
def toggle_entry(entry_id: int):
    with db() as conn:
        result = conn.execute("UPDATE entries SET done=1-done WHERE id=? AND kind != 'Nothing Tonight'", (entry_id,))
        if result.rowcount == 0:
            raise HTTPException(404, "Entry not found")
    return go()
