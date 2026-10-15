
"""Shared background synchronization status types for SyncCanvas."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SyncState(str, Enum):
    NOT_CONFIGURED = "not_configured"
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"


@dataclass(frozen=True)
class SyncResult:
    state: SyncState
    message: str
    started_at: str | None = None
    finished_at: str | None = None
