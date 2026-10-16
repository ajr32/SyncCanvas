SyncCanvas task workflow revision (#57 / #59)

REPLACE ONLY:
  synccanvas/main.py
  synccanvas/pages.py

ADD OPTIONAL TEST:
  synccanvas/tests/test_task_workflow_revision.py

No database.py replacement or migration is needed.
Existing done=0 means Not Started; done=1 means Done.
My Classes: view and add only.
Homework Review: Done on open manual tasks.
Parent Page: edit, delete (browser confirmation), confirm, return, coaching notes.
Canvas imported assignments remain read-only.

CAUTION: Parent controls are not access-protected yet; local prototype only.
Back up your existing files and SQLite database before replacing.
Run: python -m pytest synccanvas/tests -q
