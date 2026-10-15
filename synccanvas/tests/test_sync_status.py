
"""Tests for safe student-facing synchronization messages."""
import pytest

from synccanvas.models.sync_result import SyncResult, SyncState
from synccanvas.services.sync_status import present_sync_status


@pytest.mark.parametrize("state", list(SyncState))
def test_every_state_has_a_student_friendly_label(state):
    view = present_sync_status(SyncResult(state=state, message="internal"))
    assert view.state == state.value
    assert view.label
    assert view.message
    assert "internal" not in view.message


def test_error_message_never_exposes_internal_details():
    view = present_sync_status(
        SyncResult(state=SyncState.ERROR, message="secret-token-123")
    )
    assert view.label == "Update failed"
    assert "secret-token-123" not in view.message


def test_timestamps_are_preserved():
    view = present_sync_status(
        SyncResult(
            state=SyncState.SUCCESS,
            message="done",
            started_at="2026-10-15T12:00:00+00:00",
            finished_at="2026-10-15T12:00:01+00:00",
        )
    )
    assert view.started_at == "2026-10-15T12:00:00+00:00"
    assert view.finished_at == "2026-10-15T12:00:01+00:00"


def test_unknown_state_rejected():
    with pytest.raises(ValueError):
        present_sync_status(SyncResult(state="surprise", message="oops"))
