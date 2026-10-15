
"""Tests for the opt-in synchronization coordinator."""
from threading import Event

from synccanvas.models.sync_result import SyncState
from synccanvas.services.sync_coordinator import SyncCoordinator


def test_not_configured_does_not_run():
    coordinator = SyncCoordinator()
    assert coordinator.status().state == SyncState.NOT_CONFIGURED
    assert coordinator.request_sync().state == SyncState.NOT_CONFIGURED


def test_successful_worker():
    calls = []
    coordinator = SyncCoordinator(worker=lambda: calls.append("called"))
    assert coordinator.status().state == SyncState.IDLE
    coordinator.request_sync()
    result = coordinator.wait()
    assert calls == ["called"]
    assert result.state == SyncState.SUCCESS
    assert result.started_at and result.finished_at


def test_worker_failure_is_safe():
    def worker():
        raise RuntimeError("private API token")

    coordinator = SyncCoordinator(worker=worker)
    coordinator.request_sync()
    result = coordinator.wait()
    assert result.state == SyncState.ERROR
    assert "private API token" not in result.message


def test_duplicate_requests_do_not_start_second_worker():
    started, release = Event(), Event()
    calls = []

    def worker():
        calls.append(1)
        started.set()
        release.wait(timeout=5)

    coordinator = SyncCoordinator(worker=worker)
    try:
        coordinator.request_sync()
        assert started.wait(timeout=5)
        assert coordinator.request_sync().state == SyncState.RUNNING
        assert len(calls) == 1
    finally:
        release.set()
        coordinator.wait()
    assert coordinator.status().state == SyncState.SUCCESS


def test_retry_after_failure():
    attempts = []

    def worker():
        attempts.append(1)
        if len(attempts) == 1:
            raise RuntimeError("temporary")

    coordinator = SyncCoordinator(worker=worker)
    coordinator.request_sync()
    assert coordinator.wait().state == SyncState.ERROR
    coordinator.request_sync()
    assert coordinator.wait().state == SyncState.SUCCESS
    assert len(attempts) == 2
