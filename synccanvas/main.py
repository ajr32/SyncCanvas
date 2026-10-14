"""Local-only development prototype. Do not expose publicly without authentication."""
from __future__ import annotations

import html
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse

DB_PATH = Path(os.environ.get("SYNCCANVAS_DB", "synccanvas_local.sqlite3"))
KINDS = ("Homework", "Study", "Finish Classwork", "Prepare for Quiz", "Nothing Tonight", "Ask Teacher")
app = FastAPI(title="SyncCanvas (local prototype)")


@contextmanager
def db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    try:
        connection.execute("CREATE TABLE IF NOT EXISTS classes (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, sort_order INTEGER NOT NULL DEFAULT 0)")
        connection.execute("CREATE TABLE IF NOT EXISTS entries (id INTEGER PRIMARY KEY, class_id INTEGER NOT NULL REFERENCES classes(id), kind TEXT NOT NULL, details TEXT NOT NULL DEFAULT '', done INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
        connection.commit()
        yield connection
        connection.commit()
    finally:
        connection.close()


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def layout(title: str, content: str) -> HTMLResponse:
    css = """body{font-family:system-ui,Arial,sans-serif;background:#f4f7fb;color:#18253b;margin:0}header{background:#193a63;color:white;padding:18px max(20px,calc((100vw - 940px)/2))}header a{color:white;margin-right:20px}main{max-width:940px;margin:28px auto;padding:0 18px}.panel{background:white;border:1px solid #dce4ee;border-radius:12px;padding:20px;margin:16px 0}.class{border-top:1px solid #e1e8f0;padding:14px 0}input,select,button{font:inherit;padding:10px;border-radius:7px;border:1px solid #9baec4}button{background:#1659a2;color:white;border:0;cursor:pointer}label{display:block;margin:8px 0 4px}form.inline{display:inline}small{color:#52647b}.done{text-decoration:line-through;color:#64748b}.row{display:flex;flex-wrap:wrap;align-items:center;gap:10px}a{color:#1659a2}@media(max-width:580px){input,select,button{max-width:100%}.row>*{flex:1 1 170px}}"""
    return HTMLResponse(f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)} · SyncCanvas</title><style>{css}</style></head><body><header><h1>SyncCanvas</h1><nav><a href="/">Student</a><a href="/parent">Parent preview</a></nav></header><main><h2>{esc(title)}</h2>{content}<p><small>Local prototype only · No accounts or cloud sync yet · Do not publish online</small></p></main></body></html>')


@app.get("/", response_class=HTMLResponse)
def student():
    with db() as conn:
        classes = conn.execute("SELECT id,name FROM classes ORDER BY sort_order,id").fetchall()
        entries = conn.execute("SELECT id,class_id,kind,details,done FROM entries ORDER BY id DESC").fetchall()
    by_class = {}
    for entry in entries:
        by_class.setdefault(entry["class_id"], []).append(entry)
    parts = ['<section class="panel"><h3>Add a class</h3><form method="post" action="/classes"><label for="name">Class name</label><div class="row"><input id="name" name="name" required maxlength="80" placeholder="e.g. Mathematics 7"><button>Add class</button></div></form></section>']
    if not classes:
        parts.append('<section class="panel"><p>Add your first class to start recording what needs to come home.</p></section>')
    for cls in classes:
        cid = cls["id"]
        content = [f'<section class="panel"><h3>{esc(cls["name"])}</h3>']
        for item in by_class.get(cid, []):
            status = ' class="done"' if item["done"] else ''
            detail = f' — {esc(item["details"])}' if item["details"] else ''
            content.append(f'<div class="class"><span{status}><strong>{esc(item["kind"])}</strong>{detail}</span> <form class="inline" method="post" action="/entries/{item["id"]}/toggle"><button type="submit">{"Undo" if item["done"] else "Done"}</button></form></div>')
        options = ''.join(f'<option value="{esc(k)}">{esc(k)}</option>' for k in KINDS)
        content.append(f'<form method="post" action="/classes/{cid}/entries"><label for="kind-{cid}">What needs to happen?</label><select id="kind-{cid}" name="kind">{options}</select><label for="details-{cid}">Details (optional)</label><input id="details-{cid}" name="details" maxlength="300" placeholder="What exactly should I do?"><button type="submit">Save</button></form></section>')
        parts.extend(content)
    return layout("My classes", ''.join(parts))


@app.get("/parent", response_class=HTMLResponse)
def parent():
    with db() as conn:
        rows = conn.execute("SELECT c.name, e.kind, e.details, e.done FROM entries e JOIN classes c ON c.id=e.class_id ORDER BY c.sort_order,c.id,e.id DESC").fetchall()
    parts = ['<section class="panel"><p>This is a read-only preview of what the student entered. Parent authentication and verification will come later.</p>']
    if not rows:
        parts.append('<p>No entries yet.</p>')
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
    return RedirectResponse("/", status_code=303)


@app.post("/classes/{class_id}/entries")
def add_entry(class_id: int, kind: str = Form(...), details: str = Form("")):
    if kind not in KINDS or len(details) > 300:
        raise HTTPException(422, "Invalid entry")
    with db() as conn:
        if not conn.execute("SELECT 1 FROM classes WHERE id=?", (class_id,)).fetchone():
            raise HTTPException(404, "Class not found")
        conn.execute("INSERT INTO entries(class_id,kind,details) VALUES (?,?,?)", (class_id, kind, details.strip()))
    return RedirectResponse("/", status_code=303)


@app.post("/entries/{entry_id}/toggle")
def toggle_entry(entry_id: int):
    with db() as conn:
        result = conn.execute("UPDATE entries SET done=1-done WHERE id=?", (entry_id,))
        if result.rowcount == 0:
            raise HTTPException(404, "Entry not found")
    return RedirectResponse("/", status_code=303)
