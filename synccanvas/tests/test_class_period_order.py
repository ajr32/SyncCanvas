"""Regression tests for school-day class order."""
import sqlite3
from unittest.mock import patch
from datetime import date
from synccanvas.pages import get_active_classes


def make_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE classes(id INTEGER PRIMARY KEY, name TEXT, enabled INT, archived INT, sort_order INT);
        CREATE TABLE bell_periods(id INTEGER PRIMARY KEY, label TEXT, start_time TEXT, weekdays TEXT);
        CREATE TABLE class_periods(class_id INT, period_id INT);
        CREATE TABLE school_day_periods(day TEXT, period_id INT, start_time TEXT);
        CREATE TABLE school_days(day TEXT, kind TEXT);
        INSERT INTO classes VALUES(1,'Science',1,0,0),(2,'ELA',1,0,0),(3,'Unassigned',1,0,0);
        INSERT INTO bell_periods VALUES(1,'1','08:00','01234'),(2,'2','09:00','01234');
        INSERT INTO class_periods VALUES(1,2),(2,1);
    """)
    return conn


def test_periods_win_over_manual_order():
    conn = make_db()
    with patch("synccanvas.pages.family_today", return_value=date(2026,10,19)):
        assert [r["name"] for r in get_active_classes(conn)] == ["ELA","Science","Unassigned"]


def test_weekend_still_uses_period_order():
    conn = make_db()
    with patch("synccanvas.pages.family_today", return_value=date(2026,10,24)):
        assert [r["name"] for r in get_active_classes(conn)] == ["ELA","Science","Unassigned"]


def test_special_day_uses_adjusted_start():
    conn = make_db()
    conn.execute("INSERT INTO school_day_periods VALUES('2026-10-19',2,'07:30')")
    with patch("synccanvas.pages.family_today", return_value=date(2026,10,19)):
        assert [r["name"] for r in get_active_classes(conn)] == ["Science","ELA","Unassigned"]


def test_closed_day_keeps_normal_order():
    conn = make_db()
    conn.execute("INSERT INTO school_days VALUES('2026-10-19','closed')")
    with patch("synccanvas.pages.family_today", return_value=date(2026,10,19)):
        rows = get_active_classes(conn)
        assert [r["name"] for r in rows] == ["ELA","Science","Unassigned"]
        assert all(r["period_label"] is None and r["period_start"] is None for r in rows)
