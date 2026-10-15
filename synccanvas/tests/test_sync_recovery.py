
"""Failure handling and recovery tests for SyncCanvas synchronization.

Tests use fake workers only. No Canvas API, credentials, or network
access is required.
"""

from threading import Event

from synccanvas.models.sync_result import SyncState
from synccanvas.services.background_sync import BackgroundSync
from synccanvas.services.sync_coordinator import SyncCoordinator
from synccanvas.services.sync_status import present_sync_status


def test_failed_worker_returns_error():
    def worker():
        raise RuntimeError("Temporary connection failure")

    coordinator = SyncCoordinator(worker=worker)
    coordinator.request_sync()

    result = coordinator.wait()

    assert result.state == SyncState.ERROR
    assert result.started_at is not None
    assert result.finished_at is not None


def test_internal_error_is_not_exposed():
    secret = "CANVAS_TOKEN=private-secret-123"

    def worker():
        raise RuntimeError(secret)

    coordinator = SyncCoordinator(worker=worker)
    coordinator.request_sync()

    result = coordinator.wait()
    view = present_sync_status(result)

    assert result.state == SyncState.ERROR
    assert secret not in result.message
    assert secret not in view.message
    assert secret not in view.label


def test_failed_sync_can_be_retried():
    attempts = []

    def worker():
        attempts.append(1)
        if len(attempts) == 1:
            raise ConnectionError("Offline")

    coordinator = SyncCoordinator(worker=worker)

    coordinator.request_sync()
    assert coordinator.wait().state == SyncState.ERROR

    coordinator.request_sync()
    assert coordinator.wait().state == SyncState.SUCCESS

    assert len(attempts) == 2


def test_success_can_be_followed_by_another_sync():
    calls = []

    def worker():
        calls.append("run")

    coordinator = SyncCoordinator(worker=worker)

    coordinator.request_sync()
    assert coordinator.wait().state == SyncState.SUCCESS

    coordinator.request_sync()
    assert coordinator.wait().state == SyncState.SUCCESS

    assert calls == ["run", "run"]


def test_running_sync_does_not_start_duplicate():
    started = Event()
    release = Event()
    calls = []

    def worker():
        calls.append(1)
        started.set()
        release.wait(timeout=5)

    coordinator = SyncCoordinator(worker=worker)

    try:
        coordinator.request_sync()
        assert started.wait(timeout=5)

        second = coordinator.request_sync()

        assert second.state == SyncState.RUNNING
        assert len(calls) == 1
    finally:
        release.set()
        coordinator.wait()

    assert coordinator.status().state == SyncState.SUCCESS


def test_timeout_does_not_report_false_success():
    started = Event()
    release = Event()

    def worker():
        started.set()
        release.wait(timeout=5)

    coordinator = SyncCoordinator(worker=worker)

    try:
        coordinator.request_sync()
        assert started.wait(timeout=5)

        result = coordinator.wait(timeout=0.01)

        assert result.state == SyncState.RUNNING
    finally:
        release.set()
        coordinator.wait()

    assert coordinator.status().state == SyncState.SUCCESS


def test_unconfigured_sync_remains_disabled():
    coordinator = SyncCoordinator()

    before = coordinator.status()
    after = coordinator.request_sync()

    assert before.state == SyncState.NOT_CONFIGURED
    assert after.state == SyncState.NOT_CONFIGURED


def test_recovery_clears_previous_error_state():
    attempts = []

    def worker():
        attempts.append(1)
        if len(attempts) == 1:
            raise RuntimeError("First attempt failed")

    service = BackgroundSync(worker=worker)

    service.request_sync()
    failed = service.wait()

    assert failed.state == SyncState.ERROR

    service.request_sync()
    recovered = service.wait()

    assert recovered.state == SyncState.SUCCESS
    assert recovered.message == "Synchronization completed."
    assert recovered.finished_at is not None
    assert recovered.started_at is not None
