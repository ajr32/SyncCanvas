
"""Integration tests for SyncCanvas school updates and synchronization API."""

from contextlib import contextmanager
import sqlite3
from threading import Event

import pytest
from fastapi.testclient import TestClient

from synccanvas.main import app
from synccanvas.models.sync_result import SyncState
from synccanvas.services.background_sync import BackgroundSync
from synccanvas.services.sync_coordinator import SyncCoordinator


@pytest.fixture
def client(monkeypatch):
    """Isolate sync state and use an empty in-memory student database."""
    import synccanvas.main as main_module
    import synccanvas.pages as pages_module

    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.executescript(
        """
        CREATE TABLE classes (
            id INTEGER PRIMARY KEY,
            name TEXT,
            sort_order INTEGER DEFAULT 0,
            enabled INTEGER NOT NULL DEFAULT 1,
            archived INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE entries (
            id INTEGER PRIMARY KEY,
            class_id INTEGER,
            kind TEXT,
            details TEXT,
            done INTEGER DEFAULT 0,
            parent_confirmed INTEGER DEFAULT 0,
            coaching_note TEXT DEFAULT ''
        );

        CREATE TABLE checkins (
            class_id INTEGER,
            day TEXT,
            nothing_tonight INTEGER DEFAULT 0,
            PRIMARY KEY (class_id, day)
        );

        CREATE TABLE canvas_course_links (
            canvas_course_id INTEGER PRIMARY KEY,
            class_id INTEGER NOT NULL UNIQUE REFERENCES classes(id) ON DELETE CASCADE
        );

        CREATE TABLE canvas_assignments (
            id INTEGER PRIMARY KEY,
            canvas_course_id INTEGER NOT NULL,
            canvas_assignment_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            due_at TEXT,
            due_date TEXT,
            html_url TEXT,
            student_notes TEXT NOT NULL DEFAULT '',
            completed INTEGER NOT NULL DEFAULT 0,
            submission_types TEXT NOT NULL DEFAULT '[]',
            UNIQUE(canvas_course_id, canvas_assignment_id)
        );
        """
    )

    @contextmanager
    def fake_db():
        yield connection

    service = BackgroundSync()
    coordinator = SyncCoordinator(background=service)

    monkeypatch.setattr(pages_module, "db", fake_db)
    monkeypatch.setattr(pages_module, "sync_coordinator", coordinator)
    monkeypatch.setattr(main_module, "background_sync", service)
    monkeypatch.setattr(main_module, "sync_coordinator", coordinator)

    with TestClient(app) as test_client:
        yield test_client, coordinator

    connection.close()


def test_unconfigured_student_page(client):
    http, _ = client
    response = http.get("/")
    assert response.status_code == 200
    assert "School updates" in response.text
    assert "Not connected" in response.text
    assert 'action="/sync/run"' not in response.text


def test_unconfigured_api_status(client):
    http, _ = client
    response = http.get("/api/sync/status")
    assert response.status_code == 200
    assert response.json()["state"] == SyncState.NOT_CONFIGURED.value


def test_unconfigured_api_run_does_not_start_sync(client):
    http, _ = client
    response = http.post("/api/sync/run")
    assert response.status_code == 200
    assert response.json()["state"] == SyncState.NOT_CONFIGURED.value


def test_page_sync_button_redirects_safely(client):
    http, coordinator = client
    response = http.post("/sync/run", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/"
    assert coordinator.status().state == SyncState.NOT_CONFIGURED


def test_configured_worker_is_shared_by_page_and_api(client, monkeypatch):
    import synccanvas.main as main_module
    import synccanvas.pages as pages_module

    calls = []
    service = BackgroundSync(worker=lambda: calls.append("synced"))
    coordinator = SyncCoordinator(background=service)

    monkeypatch.setattr(main_module, "background_sync", service)
    monkeypatch.setattr(main_module, "sync_coordinator", coordinator)
    monkeypatch.setattr(pages_module, "sync_coordinator", coordinator)

    http, _ = client
    page = http.get("/")
    assert "School updates" in page.text
    assert 'action="/sync/run"' in page.text

    response = http.post("/sync/run", follow_redirects=False)
    assert response.status_code == 303
    assert coordinator.wait().state == SyncState.SUCCESS
    assert calls == ["synced"]
    assert http.get("/api/sync/status").json()["state"] == "success"
    assert "Up to date" in http.get("/").text


def test_running_sync_cannot_be_started_twice(client, monkeypatch):
    import synccanvas.main as main_module
    import synccanvas.pages as pages_module

    started, release = Event(), Event()
    calls = []

    def worker():
        calls.append(1)
        started.set()
        release.wait(timeout=5)

    service = BackgroundSync(worker=worker)
    coordinator = SyncCoordinator(background=service)

    monkeypatch.setattr(main_module, "background_sync", service)
    monkeypatch.setattr(main_module, "sync_coordinator", coordinator)
    monkeypatch.setattr(pages_module, "sync_coordinator", coordinator)

    http, _ = client
    try:
        assert http.post("/api/sync/run").status_code == 200
        assert started.wait(timeout=5)
        assert http.get("/api/sync/status").json()["state"] == "running"
        assert "Updating" in http.get("/").text
        assert 'action="/sync/run"' not in http.get("/").text
        assert http.post("/api/sync/run").json()["state"] == "running"
        assert calls == [1]
    finally:
        release.set()
        coordinator.wait()
