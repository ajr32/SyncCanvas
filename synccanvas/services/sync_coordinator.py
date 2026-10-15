"""Small, opt-in synchronization coordinator for the family planner.

No CanvasSync imports, network access, or automatic synchronization.
"""
from __future__ import annotations

from synccanvas.models.sync_result import SyncResult
from synccanvas.services.background_sync import BackgroundSync, SyncWorker


class SyncCoordinator:
    """Provide one consistent interface for starting and checking syncs."""

    def __init__(
        self, worker: SyncWorker | None = None, *, background: BackgroundSync | None = None
    ) -> None:
        if worker is not None and background is not None:
            raise ValueError("Provide a worker or an existing background service, not both.")
        self._background = background if background is not None else BackgroundSync(worker=worker)

    def request_sync(self) -> SyncResult:
        return self._background.request_sync()

    def status(self) -> SyncResult:
        return self._background.status()

    def wait(self, timeout: float = 5.0) -> SyncResult:
        """Primarily useful for deterministic tests."""
        return self._background.wait(timeout=timeout)


# Share the same disabled-by-default service with the existing API.
from synccanvas.services.background_sync import background_sync

sync_coordinator = SyncCoordinator(background=background_sync)
