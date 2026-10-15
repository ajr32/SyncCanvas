
"""Tests for the background synchronization interface."""

from threading import Event

from synccanvas.services.background_sync import (
    BackgroundSync,
    SyncState,
)


def test_default_sync_is_not_configured():
    result = BackgroundSync().status()

    assert result.state == SyncState.NOT_CONFIGURED
    assert result.started_at is None
    assert result.finished_at is None


def test_disabled_sync_does_not_start():
    sync = BackgroundSync()

    result = sync.request_sync()

    assert result.state == SyncState.NOT_CONFIGURED
    assert sync.status().state == SyncState.NOT_CONFIGURED


def test_successful_background_sync():
    calls = []

    def worker():
        calls.append("called")

    sync = BackgroundSync(worker=worker)

    assert sync.status().state == SyncState.IDLE

    sync.request_sync()
    result = sync.wait()

    assert calls == ["called"]
    assert result.state == SyncState.SUCCESS
    assert result.started_at is not None
    assert result.finished_at is not None


def test_failed_background_sync():
    def worker():
        raise RuntimeError("Sensitive internal failure")

    sync = BackgroundSync(worker=worker)

    sync.request_sync()
    result = sync.wait()

    assert result.state == SyncState.ERROR
    assert "failed" in result.message.lower()
    assert "Sensitive internal failure" not in result.message


def test_duplicate_request_does_not_start_second_worker():
    started = Event()
    release = Event()
    calls = []

    def worker():
        calls.append("called")
        started.set()
        release.wait(timeout=5)

    sync = BackgroundSync(worker=worker)

    try:
        first = sync.request_sync()

        assert first.state == SyncState.RUNNING
        assert started.wait(timeout=5)

        second = sync.request_sync()

        assert second.state == SyncState.RUNNING
        assert calls == ["called"]

    finally:
        release.set()
        sync.wait()

    assert sync.status().state == SyncState.SUCCESS


def test_retry_after_failure():
    attempts = []

    def worker():
        attempts.append(1)

        if len(attempts) == 1:
            raise RuntimeError("Temporary failure")

    sync = BackgroundSync(worker=worker)

    sync.request_sync()
    assert sync.wait().state == SyncState.ERROR

    sync.request_sync()
    assert sync.wait().state == SyncState.SUCCESS

    assert len(attempts) == 2
