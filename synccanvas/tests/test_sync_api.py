
"""Tests for SyncCanvas background synchronization endpoints."""

from threading import Event

import pytest
from fastapi.testclient import TestClient

from synccanvas import main
from synccanvas.services.background_sync import (
    BackgroundSync,
)


@pytest.fixture
def client(monkeypatch):
    """Start each test with an isolated sync interface."""
    sync = BackgroundSync()
    monkeypatch.setattr(main, "background_sync", sync)

    with TestClient(main.app) as test_client:
        yield test_client


def test_sync_status_not_configured(client):
    response = client.get("/api/sync/status")

    assert response.status_code == 200

    data = response.json()

    assert data["state"] == "not_configured"
    assert data["started_at"] is None
    assert data["finished_at"] is None
    assert "not configured" in data["message"].lower()


def test_sync_run_not_configured(client):
    response = client.post("/api/sync/run")

    assert response.status_code == 200
    assert response.json()["state"] == "not_configured"

    status = client.get("/api/sync/status")
    assert status.json()["state"] == "not_configured"


def test_sync_api_success(client, monkeypatch):
    calls = []

    def worker():
        calls.append("ran")

    sync = BackgroundSync(worker=worker)
    monkeypatch.setattr(main, "background_sync", sync)

    response = client.post("/api/sync/run")

    assert response.status_code == 200
    assert response.json()["state"] in ("running", "success")

    result = sync.wait()

    assert result.state.value == "success"
    assert calls == ["ran"]

    status = client.get("/api/sync/status").json()

    assert status["state"] == "success"
    assert status["started_at"] is not None
    assert status["finished_at"] is not None


def test_sync_api_failure(client, monkeypatch):
    def worker():
        raise RuntimeError("Private credential information")

    sync = BackgroundSync(worker=worker)
    monkeypatch.setattr(main, "background_sync", sync)

    response = client.post("/api/sync/run")
    assert response.status_code == 200

    sync.wait()

    status = client.get("/api/sync/status").json()

    assert status["state"] == "error"
    assert "failed" in status["message"].lower()
    assert "Private credential information" not in str(status)


def test_sync_api_duplicate_request(client, monkeypatch):
    started = Event()
    release = Event()
    calls = []

    def worker():
        calls.append("ran")
        started.set()
        release.wait(timeout=5)

    sync = BackgroundSync(worker=worker)
    monkeypatch.setattr(main, "background_sync", sync)

    try:
        first = client.post("/api/sync/run")
        assert first.status_code == 200

        assert started.wait(timeout=5)

        second = client.post("/api/sync/run")

        assert second.status_code == 200
        assert second.json()["state"] == "running"
        assert calls == ["ran"]

    finally:
        release.set()
        sync.wait()

    assert (
        client.get("/api/sync/status").json()["state"]
        == "success"
    )
