"""Planning-date and grouping regression tests."""
import sqlite3
from datetime import date, timedelta
from synccanvas.pages import ensure_canvas_planning, effective_canvas_date, afternoon_bucket


def test_parent_planning_table_is_idempotent():
    conn = sqlite3.connect(":memory:")
    ensure_canvas_planning(conn)
    ensure_canvas_planning(conn)
    conn.execute("INSERT INTO canvas_family_planning VALUES (1, '2026-10-20', 1)")
    assert conn.execute("SELECT show_now FROM canvas_family_planning").fetchone()[0] == 1


def test_buckets_and_override():
    cutoff = "2026-10-21"
    far = "2026-12-18"
    def item(due=None, plan=None, now=0):
        return {"due_date": due, "planning_date": plan, "show_now": now}
    assert afternoon_bucket(item("2026-10-21"), cutoff, far) == "current"
    assert afternoon_bucket(item("2026-11-01"), cutoff, far) == "future"
    assert afternoon_bucket(item("2027-05-01"), cutoff, far) == "far"
    assert afternoon_bucket(item(), cutoff, far) == "undated"
    assert afternoon_bucket(item("2027-05-01", "2026-10-20"), cutoff, far) == "current"
    assert afternoon_bucket(item("2027-05-01", now=1), cutoff, far) == "current"
    assert effective_canvas_date(item("2027-05-01", "2026-10-20")) == "2026-10-20"
