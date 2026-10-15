
"""Student-friendly, safe display of synchronization status."""
from __future__ import annotations

from dataclasses import dataclass

from synccanvas.models.sync_result import SyncResult, SyncState


@dataclass(frozen=True)
class SyncStatusView:
    state: str
    label: str
    message: str
    started_at: str | None
    finished_at: str | None


_LABELS = {
    SyncState.NOT_CONFIGURED: "Not connected",
    SyncState.IDLE: "Ready",
    SyncState.RUNNING: "Updating",
    SyncState.SUCCESS: "Up to date",
    SyncState.ERROR: "Update failed",
}

_MESSAGES = {
    SyncState.NOT_CONFIGURED: "School updates are not connected yet.",
    SyncState.IDLE: "Ready to check for school updates.",
    SyncState.RUNNING: "Checking for school updates...",
    SyncState.SUCCESS: "School updates checked successfully.",
    SyncState.ERROR: "Couldn't check for updates. Try again later.",
}


def present_sync_status(result: SyncResult) -> SyncStatusView:
    """Map internal state to safe UI text; never expose worker errors."""
    state = SyncState(result.state)
    return SyncStatusView(
        state=state.value,
        label=_LABELS[state],
        message=_MESSAGES[state],
        started_at=result.started_at,
        finished_at=result.finished_at,
    )
