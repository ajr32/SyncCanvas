
"""Test safe replacement of Google Calendar OAuth tokens.

No real Google API requests or browser authorization.
"""

import json
import sys
import types

import pytest

from scripts import setup_class_calendars as setup


class FakeCredentials:
    def __init__(self, valid=True):
        self.valid = valid

    def to_json(self):
        return json.dumps({
            "access_token": "new-test-token",
            "valid": self.valid,
        })


class FakeRequest:
    def __init__(self, fails=False):
        self.fails = fails

    def execute(self, **kwargs):
        if self.fails:
            raise RuntimeError("Google verification failed")
        return {"items": []}


class FakeCalendarList:
    def __init__(self, fails=False):
        self.fails = fails

    def list(self, **kwargs):
        return FakeRequest(self.fails)


class FakeService:
    def __init__(self, fails=False):
        self.fails = fails

    def calendarList(self):
        return FakeCalendarList(self.fails)


@pytest.fixture
def reconnect_environment(monkeypatch, tmp_path):
    monkeypatch.setattr(setup, "ROOT", tmp_path)

    token_path = tmp_path / "synccanvas_google_token.json"
    credentials_path = (
        tmp_path / "synccanvas_google_credentials.json"
    )

    token_path.write_text("original-token")
    credentials_path.write_text("{}")

    state = {
        "credentials": FakeCredentials(),
        "verification_fails": False,
        "authorization_fails": False,
    }

    oauthlib = types.ModuleType("google_auth_oauthlib")
    oauthlib.__path__ = []

    flow_module = types.ModuleType("google_auth_oauthlib.flow")

    class FakeFlow:
        @classmethod
        def from_client_secrets_file(cls, filename, scopes):
            return cls()

        def run_local_server(self, **kwargs):
            if state["authorization_fails"]:
                raise RuntimeError("Authorization cancelled")
            return state["credentials"]

    flow_module.InstalledAppFlow = FakeFlow

    api = types.ModuleType("googleapiclient")
    api.__path__ = []

    discovery = types.ModuleType("googleapiclient.discovery")

    discovery.build = lambda *args, **kwargs: FakeService(
        state["verification_fails"]
    )

    monkeypatch.setitem(
        sys.modules, "google_auth_oauthlib", oauthlib
    )
    monkeypatch.setitem(
        sys.modules, "google_auth_oauthlib.flow", flow_module
    )
    monkeypatch.setitem(
        sys.modules, "googleapiclient", api
    )
    monkeypatch.setitem(
        sys.modules, "googleapiclient.discovery", discovery
    )

    return state, token_path, credentials_path


def test_successful_reconnect_replaces_token(
    reconnect_environment,
):
    state, token_path, _ = reconnect_environment

    setup.reconnect_google_calendar()

    saved = json.loads(token_path.read_text())

    assert saved["access_token"] == "new-test-token"
    assert saved["valid"] is True


def test_cancelled_authorization_preserves_token(
    reconnect_environment,
):
    state, token_path, _ = reconnect_environment
    state["authorization_fails"] = True

    with pytest.raises(RuntimeError, match="cancelled"):
        setup.reconnect_google_calendar()

    assert token_path.read_text() == "original-token"


def test_failed_google_verification_preserves_token(
    reconnect_environment,
):
    state, token_path, _ = reconnect_environment
    state["verification_fails"] = True

    with pytest.raises(RuntimeError, match="verification failed"):
        setup.reconnect_google_calendar()

    assert token_path.read_text() == "original-token"


def test_invalid_new_credentials_preserve_token(
    reconnect_environment,
):
    state, token_path, _ = reconnect_environment
    state["credentials"] = FakeCredentials(valid=False)

    with pytest.raises(RuntimeError, match="did not complete"):
        setup.reconnect_google_calendar()

    assert token_path.read_text() == "original-token"


def test_missing_client_credentials_preserves_token(
    reconnect_environment,
):
    state, token_path, credentials_path = reconnect_environment
    credentials_path.unlink()

    with pytest.raises(RuntimeError, match="Missing"):
        setup.reconnect_google_calendar()

    assert token_path.read_text() == "original-token"


def test_successful_reconnect_leaves_no_temp_files(
    reconnect_environment,
):
    state, token_path, _ = reconnect_environment

    setup.reconnect_google_calendar()

    leftovers = list(
        token_path.parent.glob(
            ".synccanvas_google_token_*.tmp"
        )
    )

    assert leftovers == []
