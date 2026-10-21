
"""Tests for #136: safe Google Calendar authentication."""

import json
import sys
import types

import pytest

from scripts import setup_class_calendars as setup


class FakeRefreshError(Exception):
    pass


class FakeCredentials:
    current = None

    def __init__(
        self,
        *,
        valid=True,
        expired=False,
        refresh_token=None,
        refresh_fails=False,
    ):
        self.valid = valid
        self.expired = expired
        self.refresh_token = refresh_token
        self.refresh_fails = refresh_fails
        self.refresh_calls = 0

    @classmethod
    def from_authorized_user_file(cls, filename, scopes):
        return cls.current

    def refresh(self, request):
        self.refresh_calls += 1

        if self.refresh_fails:
            raise FakeRefreshError("Token revoked")

        self.valid = True
        self.expired = False

    def to_json(self):
        return json.dumps({"valid": self.valid})


@pytest.fixture
def google_auth(monkeypatch, tmp_path):
    monkeypatch.setattr(setup, "ROOT", tmp_path)

    def module(name):
        obj = types.ModuleType(name)
        monkeypatch.setitem(sys.modules, name, obj)
        return obj

    google = module("google")
    google.__path__ = []

    auth = module("google.auth")
    auth.__path__ = []
    google.auth = auth

    exceptions = module("google.auth.exceptions")
    exceptions.RefreshError = FakeRefreshError

    transport = module("google.auth.transport")
    transport.__path__ = []

    requests = module("google.auth.transport.requests")
    requests.Request = lambda: object()

    oauth2 = module("google.oauth2")
    oauth2.__path__ = []

    credentials = module("google.oauth2.credentials")
    credentials.Credentials = FakeCredentials

    oauthlib = module("google_auth_oauthlib")
    oauthlib.__path__ = []

    flow_module = module("google_auth_oauthlib.flow")

    class FakeFlow:
        @classmethod
        def from_client_secrets_file(cls, filename, scopes):
            return cls()

        def run_local_server(self, **kwargs):
            return FakeCredentials.current

    flow_module.InstalledAppFlow = FakeFlow

    api = module("googleapiclient")
    api.__path__ = []

    discovery = module("googleapiclient.discovery")
    discovery.build = (
        lambda name, version, credentials:
        {"service": name, "credentials": credentials}
    )

    token_path = tmp_path / "synccanvas_google_token.json"
    credentials_path = (
        tmp_path / "synccanvas_google_credentials.json"
    )

    FakeCredentials.current = None

    yield token_path, credentials_path

    FakeCredentials.current = None


def test_valid_token_connects(google_auth):
    token_path, _ = google_auth
    token_path.write_text("old token")

    credentials = FakeCredentials(valid=True)
    FakeCredentials.current = credentials

    service = setup.google_service()

    assert service["service"] == "calendar"
    assert service["credentials"] is credentials
    assert credentials.refresh_calls == 0


def test_expired_token_refreshes(google_auth):
    token_path, _ = google_auth
    token_path.write_text("old token")

    credentials = FakeCredentials(
        valid=False,
        expired=True,
        refresh_token="refresh-token",
    )
    FakeCredentials.current = credentials

    service = setup.google_service()

    assert service["service"] == "calendar"
    assert credentials.refresh_calls == 1
    assert credentials.valid
    assert json.loads(token_path.read_text())["valid"]


def test_revoked_token_does_not_overwrite_saved_token(
    google_auth,
):
    token_path, _ = google_auth
    original = "important existing token"
    token_path.write_text(original)

    FakeCredentials.current = FakeCredentials(
        valid=False,
        expired=True,
        refresh_token="revoked-token",
        refresh_fails=True,
    )

    with pytest.raises(RuntimeError, match="Reconnect"):
        setup.google_service()

    assert token_path.read_text() == original


def test_expired_token_without_refresh_token_is_safe(
    google_auth,
):
    token_path, _ = google_auth
    original = "existing token"
    token_path.write_text(original)

    FakeCredentials.current = FakeCredentials(
        valid=False,
        expired=True,
        refresh_token=None,
    )

    with pytest.raises(RuntimeError, match="reconnected"):
        setup.google_service()

    assert token_path.read_text() == original


def test_missing_credentials_does_not_create_token(
    google_auth,
):
    token_path, _ = google_auth

    with pytest.raises(RuntimeError, match="Missing"):
        setup.google_service()

    assert not token_path.exists()


def test_first_authorization_saves_valid_token(
    google_auth,
):
    token_path, credentials_path = google_auth
    credentials_path.write_text("{}")

    FakeCredentials.current = FakeCredentials(valid=True)

    service = setup.google_service()

    assert service["service"] == "calendar"
    assert token_path.exists()
    assert json.loads(token_path.read_text())["valid"]


def test_failed_first_authorization_does_not_save_token(
    google_auth,
):
    token_path, credentials_path = google_auth
    credentials_path.write_text("{}")

    FakeCredentials.current = FakeCredentials(valid=False)

    with pytest.raises(RuntimeError, match="did not complete"):
        setup.google_service()

    assert not token_path.exists()
