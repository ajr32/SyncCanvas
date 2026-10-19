
"""Background synchronization interface for CeeEss / SyncCanvas.

This module does not import or modify the legacy CanvasSync project.
A sync worker must be explicitly supplied before synchronization can run.

Status is stored in memory only. It resets when the application restarts.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from threading import Lock, Thread
from typing import Protocol

from synccanvas.models.sync_result import SyncResult, SyncState


class SyncWorker(Protocol):
    """Contract for a future Canvas read-only importer."""

    def __call__(self) -> None:
        """Perform one synchronization attempt."""
        ...


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


class BackgroundSync:
    """Manage one background sync at a time."""

    def __init__(
        self,
        worker: SyncWorker | None = None,
    ):
        self._worker = worker
        self._lock = Lock()
        self._thread: Thread | None = None

        if worker is None:
            self._result = SyncResult(
                state=SyncState.NOT_CONFIGURED,
                message="Synchronization is not configured yet.",
            )
        else:
            self._result = SyncResult(
                state=SyncState.IDLE,
                message="Ready to synchronize.",
            )

    def configure(self, worker: SyncWorker) -> None:
        """Install an explicit worker without replacing this shared service.

        Configuration is allowed only while synchronization is not running.
        """
        if not callable(worker):
            raise ValueError("A callable synchronization worker is required.")
        with self._lock:
            if self._result.state == SyncState.RUNNING:
                raise RuntimeError("Cannot configure while synchronization is running.")
            self._worker = worker
            self._result = SyncResult(
                state=SyncState.IDLE,
                message="Ready to synchronize.",
            )

    def status(self) -> SyncResult:
        """Return the current synchronization status."""
        with self._lock:
            return self._result

    def request_sync(self) -> SyncResult:
        """Start one sync without blocking the caller.

        Requests made while a sync is running do not start
        a second worker.
        """
        with self._lock:
            if self._worker is None:
                return self._result

            if self._result.state == SyncState.RUNNING:
                return self._result

            started = timestamp()

            self._result = SyncResult(
                state=SyncState.RUNNING,
                message="Synchronization is running.",
                started_at=started,
            )

            thread = Thread(
                target=self._run,
                args=(self._worker, started),
                daemon=True,
                name="synccanvas-background-sync",
            )

            self._thread = thread
            thread.start()

            return self._result

    def _run(
        self,
        worker: SyncWorker,
        started: str,
    ) -> None:
        try:
            worker()
        except Exception:
            logging.getLogger("synccanvas.reliability").error("sync_failed")
            # Do not expose tokens, credentials, or exception
            # details through student/parent status messages.
            result = SyncResult(
                state=SyncState.ERROR,
                message=(
                    "Synchronization failed. "
                    "Please try again later."
                ),
                started_at=started,
                finished_at=timestamp(),
            )
        else:
            logging.getLogger("synccanvas.reliability").info("sync_succeeded")
            result = SyncResult(
                state=SyncState.SUCCESS,
                message="Synchronization completed.",
                started_at=started,
                finished_at=timestamp(),
            )

        with self._lock:
            self._result = result

    def wait(self, timeout: float = 5.0) -> SyncResult:
        """Wait for the current worker, primarily for tests."""
        with self._lock:
            thread = self._thread

        if thread is not None:
            thread.join(timeout=timeout)

        return self.status()


# Default family-planner instance.
# No external synchronization is enabled.
background_sync = BackgroundSync()
