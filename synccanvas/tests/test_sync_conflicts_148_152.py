"""Regression checks for safe Canvas/family separation and import provenance."""
import sqlite3
from synccanvas import database, pages
from synccanvas.services.canvas_import_worker import CanvasImportWorker
from synccanvas.services.canvas_storage import link_canvas_course


def test_missing_canvas_item_preserves_linked_family_task(tmp_path, monkeypatch):
    monkeypatch.setattr(database, 'DB_PATH', tmp_path / 'family.sqlite3')
    with database.db() as conn:
        conn.execute("INSERT INTO classes(id,name) VALUES(1,'ELA')")
        link_canvas_course(conn, 99, 1)
        conn.execute("""INSERT INTO canvas_assignments(id,canvas_course_id,canvas_assignment_id,title,due_date)
                     VALUES(20,99,200,'Original quiz','2026-10-20')""")
        conn.execute("""INSERT INTO entries(id,class_id,kind,details,due_date,origin)
                     VALUES(30,1,'Study','Study together','2026-10-19','parent')""")
        conn.execute('INSERT INTO entry_canvas_links(entry_id,canvas_assignment_id) VALUES(30,20)')
    worker = CanvasImportWorker(fetch_assignments=lambda course_id: [])
    worker.run()
    with database.db() as conn:
        task = conn.execute('SELECT details,due_date,done FROM entries WHERE id=30').fetchone()
        assignment = conn.execute('SELECT missing_from_canvas FROM canvas_assignments WHERE id=20').fetchone()
        linked = conn.execute('SELECT canvas_assignment_id FROM entry_canvas_links WHERE entry_id=30').fetchone()
        audit = conn.execute('SELECT last_success_at FROM canvas_sync_audit WHERE id=1').fetchone()
        assert tuple(task) == ('Study together','2026-10-19',0)
        assert assignment['missing_from_canvas'] == 1
        assert linked['canvas_assignment_id'] == 20
        assert audit['last_success_at']
        assert 'Dates differ' in pages.home().body.decode()
        assert 'no longer found' in pages.home().body.decode()


def test_failed_fetch_does_not_mark_item_missing_or_update_audit(tmp_path, monkeypatch):
    monkeypatch.setattr(database, 'DB_PATH', tmp_path / 'family.sqlite3')
    with database.db() as conn:
        conn.execute("INSERT INTO classes(id,name) VALUES(1,'ELA')")
        link_canvas_course(conn, 99, 1)
        conn.execute("INSERT INTO canvas_assignments(id,canvas_course_id,canvas_assignment_id,title) VALUES(20,99,200,'Quiz')")
    def unavailable(course_id):
        raise ConnectionError('offline')
    worker = CanvasImportWorker(fetch_assignments=unavailable)
    try:
        worker.run()
        assert False, 'expected failure'
    except ConnectionError:
        pass
    with database.db() as conn:
        assert conn.execute('SELECT missing_from_canvas FROM canvas_assignments WHERE id=20').fetchone()[0] == 0
        assert conn.execute('SELECT COUNT(*) FROM canvas_sync_audit').fetchone()[0] == 0
