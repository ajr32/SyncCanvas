"""Parent-configured recurring Lunch Buddies activities."""

import sqlite3
from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import RedirectResponse
from synccanvas.database import db
from synccanvas.pages import esc, layout, american_time

router = APIRouter(prefix="/parent/lunch-buddies")
DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def redirect():
    return RedirectResponse("/parent/lunch-buddies", status_code=303)


def problem(message):
    result = layout("Lunch Buddies error", f'<section class="panel"><p>{esc(message)}</p><a href="/parent/lunch-buddies">Back</a></section>')
    result.status_code = 400
    return result


def validate(name, period_id, days):
    name = name.strip()
    if not 1 <= len(name) <= 80:
        raise ValueError("Activity name must contain 1–80 characters.")
    if not days or any(day not in "0123456" for day in days):
        raise ValueError("Choose at least one meeting day.")
    return name, period_id, "".join(sorted(set(days)))


@router.get("")
def index():
    with db() as conn:
        periods = conn.execute("SELECT id,label,start_time,end_time,weekdays FROM bell_periods ORDER BY start_time,id").fetchall()
        activities = conn.execute("""SELECT a.*, p.label AS period_label, p.start_time, p.end_time, p.weekdays AS period_days
            FROM lunch_buddies a JOIN bell_periods p ON p.id=a.period_id
            ORDER BY p.start_time,a.name,a.id""").fetchall()
    parts = ['<section class="panel"><p><a href="/parent">← Parent Page</a></p>',
             '<h3>Add Lunch Buddies activity</h3>',
             '<p>Activities appear on My Classes only on their scheduled days.</p>']
    if not periods:
        parts.append('<p>First <a href="/parent/schedule">create a bell period</a> for lunch.</p>')
    else:
        parts += ['<form method="post" action="/parent/lunch-buddies/add">',
                  '<label>Activity name</label><input name="name" maxlength="80" required placeholder="Lunch Buddies">',
                  '<label>Bell period</label><select name="period_id">']
        for period in periods:
            parts.append(f'<option value="{period["id"]}">Period {esc(period["label"])} ({esc(american_time(period["start_time"]))}–{esc(american_time(period["end_time"]))})</option>')
        parts.append('</select><p>Meeting days:</p>')
        for i, day in enumerate(DAYS):
            parts.append(f'<label style="display:inline-block;margin-right:12px"><input type="checkbox" name="days" value="{i}" {"checked" if i < 5 else ""}> {day}</label>')
        parts.append('<p><button type="submit">Add activity</button></p></form>')
    parts.append('</section>')
    for activity in activities:
        aid = activity["id"]
        parts += [f'<section class="panel"><h3>{esc(activity["name"])}</h3>',
                  f'<p>Period {esc(activity["period_label"])} · {esc(american_time(activity["start_time"]))}–{esc(american_time(activity["end_time"]))}</p>',
                  f'<form method="post" action="/parent/lunch-buddies/{aid}/update">',
                  f'<label>Activity name</label><input name="name" maxlength="80" required value="{esc(activity["name"])}">',
                  '<label>Bell period</label><select name="period_id">']
        for period in periods:
            selected = ' selected' if period['id'] == activity['period_id'] else ''
            parts.append(f'<option value="{period["id"]}"{selected}>Period {esc(period["label"])} ({esc(american_time(period["start_time"]))}–{esc(american_time(period["end_time"]))})</option>')
        parts.append('</select><p>Meeting days:</p>')
        for i, day in enumerate(DAYS):
            checked = 'checked' if str(i) in activity['weekdays'] else ''
            parts.append(f'<label style="display:inline-block;margin-right:12px"><input type="checkbox" name="days" value="{i}" {checked}> {day}</label>')
        parts += ['<p><button type="submit">Save activity</button></p></form>',
                  f'<form method="post" action="/parent/lunch-buddies/{aid}/delete" onsubmit="return confirm(\'Delete this activity?\');"><button class="danger" type="submit">Delete activity</button></form></section>']
    if not activities:
        parts.append('<section class="panel"><p>No Lunch Buddies activities configured yet.</p></section>')
    return layout("Lunch Buddies", ''.join(parts))


def save(name, period_id, days, activity_id=None):
    name, period_id, weekdays = validate(name, period_id, days)
    with db() as conn:
        period = conn.execute('SELECT weekdays FROM bell_periods WHERE id=?', (period_id,)).fetchone()
        if period is None:
            raise ValueError('Choose an existing bell period.')
        if any(day not in period['weekdays'] for day in weekdays):
            raise ValueError('Activity days must also be meeting days for the selected period.')
        if activity_id is None:
            conn.execute('INSERT INTO lunch_buddies(name,period_id,weekdays) VALUES(?,?,?)', (name, period_id, weekdays))
        else:
            result = conn.execute('UPDATE lunch_buddies SET name=?,period_id=?,weekdays=? WHERE id=?', (name, period_id, weekdays, activity_id))
            if not result.rowcount:
                raise ValueError('Activity not found.')


@router.post('/add')
def add(name: str = Form(...), period_id: int = Form(...), days: list[str] = Form([])):
    try:
        save(name, period_id, days)
    except (ValueError, sqlite3.IntegrityError) as exc:
        return problem(str(exc))
    return redirect()


@router.post('/{activity_id}/update')
def update(activity_id: int, name: str = Form(...), period_id: int = Form(...), days: list[str] = Form([])):
    try:
        save(name, period_id, days, activity_id)
    except (ValueError, sqlite3.IntegrityError) as exc:
        return problem(str(exc))
    return redirect()


@router.post('/{activity_id}/delete')
def delete(activity_id: int):
    with db() as conn:
        conn.execute('DELETE FROM lunch_buddies WHERE id=?', (activity_id,))
    return redirect()


# Lunch tasks use the same student -> done -> parent review lifecycle
# as ordinary homework, but belong to an activity instead of a class.
@router.post('/{activity_id}/tasks')
def add_task(activity_id: int, details: str = Form(...)):
    details = details.strip()
    if not 1 <= len(details) <= 300:
        raise HTTPException(422, 'Task or note must be 1–300 characters.')
    with db() as conn:
        activity = conn.execute('SELECT 1 FROM lunch_buddies WHERE id=?', (activity_id,)).fetchone()
        if not activity:
            raise HTTPException(404, 'Lunch Buddies activity not found.')
        conn.execute('INSERT INTO lunch_tasks(activity_id,details) VALUES(?,?)', (activity_id, details))
    return RedirectResponse('/', status_code=303)


@router.post('/tasks/{task_id}/done')
def mark_done(task_id: int):
    with db() as conn:
        result = conn.execute('UPDATE lunch_tasks SET done=1,parent_confirmed=0 WHERE id=? AND done=0', (task_id,))
        if not result.rowcount:
            raise HTTPException(409, 'Task not found or already done.')
    return RedirectResponse('/home', status_code=303)


@router.post('/tasks/{task_id}/confirm')
def confirm(task_id: int):
    with db() as conn:
        result = conn.execute('UPDATE lunch_tasks SET parent_confirmed=1 WHERE id=? AND done=1 AND parent_confirmed=0', (task_id,))
        if not result.rowcount:
            raise HTTPException(409, 'Task not ready for confirmation.')
    return RedirectResponse('/parent', status_code=303)


@router.post('/tasks/{task_id}/return')
def return_task(task_id: int):
    with db() as conn:
        result = conn.execute('UPDATE lunch_tasks SET done=0,parent_confirmed=0 WHERE id=? AND done=1', (task_id,))
        if not result.rowcount:
            raise HTTPException(409, 'Task not ready to return.')
    return RedirectResponse('/parent', status_code=303)


@router.post('/tasks/{task_id}/note')
def note(task_id: int, note: str = Form('')):
    note = note.strip()
    if len(note) > 300:
        raise HTTPException(422, 'Coaching note must be 300 characters or fewer.')
    with db() as conn:
        result = conn.execute('UPDATE lunch_tasks SET coaching_note=? WHERE id=?', (note, task_id))
        if not result.rowcount:
            raise HTTPException(404, 'Task not found.')
    return RedirectResponse('/parent', status_code=303)


@router.post('/tasks/{task_id}/delete')
def delete_task(task_id: int):
    with db() as conn:
        result = conn.execute('DELETE FROM lunch_tasks WHERE id=?', (task_id,))
        if not result.rowcount:
            raise HTTPException(404, 'Task not found.')
    return RedirectResponse('/parent', status_code=303)
