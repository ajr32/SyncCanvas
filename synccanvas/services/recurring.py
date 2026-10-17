"""Generate one parent-configured expectation per applicable day.

Only called when a plan is viewed; no external scheduler is required.
"""
from datetime import date


def ensure_today(conn, day=None):
    day = day or date.today()
    if isinstance(day, str):
        day = date.fromisoformat(day)
    day_text = day.isoformat()
    rows = conn.execute("""SELECT r.* FROM recurring_expectations r
        JOIN classes c ON c.id=r.class_id
        WHERE r.enabled=1 AND c.enabled=1 AND c.archived=0""").fetchall()
    for row in rows:
        if row['frequency'] == 'weekdays' and day.weekday() >= 5:
            continue
        # Keep generated tasks even when the parent later disables the rule.
        existing = conn.execute("""SELECT 1 FROM recurring_instances
            WHERE expectation_id=? AND work_date=?""", (row['id'], day_text)).fetchone()
        if existing:
            continue
        cursor = conn.execute("""INSERT INTO entries(class_id,kind,details,origin,planned_date)
            VALUES (?,?,?,'parent',?)""",
            (row['class_id'],row['kind'],row['details'],day_text))
        conn.execute("""INSERT INTO recurring_instances(expectation_id,work_date,entry_id)
            VALUES (?,?,?)""",(row['id'],day_text,cursor.lastrowid))
