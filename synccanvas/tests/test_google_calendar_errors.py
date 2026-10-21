
"""Tests for parent-facing Google Calendar errors."""

import pytest

from synccanvas import google_calendar_admin as admin


def error_html(exception):
    """Convert the FastAPI response into testable HTML text."""
    response = admin.calendar_error(exception)
    return response.body.decode("utf-8")


@pytest.mark.parametrize(
    "message",
    [
        "Google Calendar authorization has expired or been revoked.",
        "Google Calendar needs to be reconnected.",
        "Reconnect Google Calendar.",
    ],
)
def test_authentication_errors_request_reconnection(message):
    html = error_html(RuntimeError(message))

    assert "Reconnect Google Calendar" in html
    assert "SyncCanvas assignments and progress" in html


def test_network_error_shows_connection_message():
    html = error_html(
        ConnectionError("Network unavailable")
    )

    assert "Google Calendar connection unavailable" in html
    assert "Reconnect your Google account" not in html


def test_credentials_are_not_exposed():
    secret = "super-secret-token-123"

    html = error_html(
        RuntimeError(f"Google connection failed: {secret}")
    )

    assert secret not in html


def test_error_message_contains_navigation():
    html = error_html(
        RuntimeError("Authorization revoked")
    )

    assert "/parent/admin/google-calendar" in html
