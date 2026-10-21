
"""Tests for #136 Google Calendar reconnection."""

from types import SimpleNamespace

from synccanvas import google_calendar_admin as admin
from scripts import setup_class_calendars as setup


def fake_request(
    peer="127.0.0.1",
    hostname="localhost",
    origin=None,
    fetch_site="same-origin",
):
    from starlette.requests import Request

    headers = [(b"host", f"{hostname}:8000".encode())]

    if origin:
        headers.append((b"origin", origin.encode()))

    if fetch_site:
        headers.append(
            (b"sec-fetch-site", fetch_site.encode())
        )

    scope = {
        "type": "http",
        "method": "POST",
        "scheme": "http",
        "path": "/parent/admin/google-calendar/reconnect",
        "query_string": b"",
        "headers": headers,
        "client": (peer, 50000),
        "server": ("127.0.0.1", 8000),
    }

    return Request(scope)


def test_local_request_is_allowed():
    request = fake_request(
        origin="http://localhost:8000"
    )

    assert admin.is_local_request(request)


def test_remote_request_is_rejected():
    request = fake_request(peer="192.168.1.50")

    assert not admin.is_local_request(request)


def test_remote_hostname_is_rejected():
    request = fake_request(hostname="192.168.1.160")

    assert not admin.is_local_request(request)


def test_cross_origin_request_is_rejected():
    request = fake_request(
        origin="http://another-site.example"
    )

    assert not admin.is_local_request(request)


def test_cross_site_request_is_rejected():
    request = fake_request(fetch_site="cross-site")

    assert not admin.is_local_request(request)


def test_remote_request_never_starts_authorization(monkeypatch):
    calls = []

    monkeypatch.setattr(
        setup,
        "reconnect_google_calendar",
        lambda: calls.append("called"),
    )

    response = admin.reconnect(
        fake_request(peer="192.168.1.50")
    )

    assert response.status_code == 403
    assert calls == []


def test_local_reconnect_success(monkeypatch):
    calls = []

    monkeypatch.setattr(
        setup,
        "reconnect_google_calendar",
        lambda: calls.append("called"),
    )

    response = admin.reconnect(fake_request())

    assert calls == ["called"]
    assert b"Google Calendar reconnected" in response.body


def test_failed_reconnect_shows_safe_error(monkeypatch):
    def fail():
        raise RuntimeError("Authorization revoked")

    monkeypatch.setattr(
        setup,
        "reconnect_google_calendar",
        fail,
    )

    response = admin.reconnect(fake_request())

    assert b"Reconnect Google Calendar" in response.body
    assert b"SyncCanvas assignments and progress" in response.body
