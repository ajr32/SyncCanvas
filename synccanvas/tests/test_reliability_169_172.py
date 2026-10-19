"""Regression checks for reliability work group #169-172."""
import io
import json
import logging
from urllib.error import HTTPError, URLError

from fastapi.testclient import TestClient
from synccanvas.main import app
from synccanvas.services.canvas_http import CanvasHTTP
from synccanvas.services.canvas_reader import CanvasReadError
from synccanvas.services.background_sync import BackgroundSync, SyncState


class Response(io.BytesIO):
    def __init__(self):
        super().__init__(json.dumps([]).encode())
        self.headers = {}


def test_transient_503_retries_then_succeeds():
    attempts = []
    delays = []
    def opener(req, timeout):
        attempts.append(1)
        if len(attempts) < 3:
            raise HTTPError(req.full_url, 503, "private", {}, None)
        return Response()
    client = CanvasHTTP("https://school.example", "secret", opener=opener, sleeper=delays.append)
    assert client.get_list("/api/v1/courses") == []
    assert len(attempts) == 3
    assert delays == [0.2, 0.4]


def test_access_denied_never_retries():
    attempts = []
    def opener(req, timeout):
        attempts.append(1)
        raise HTTPError(req.full_url, 401, "private", {}, None)
    client = CanvasHTTP("https://school.example", "secret", opener=opener, sleeper=lambda _: None)
    try:
        client.get_list("/api/v1/courses")
    except CanvasReadError as exc:
        assert "denied" in str(exc)
    else:
        assert False
    assert len(attempts) == 1


def test_network_error_does_not_leak_details():
    def opener(req, timeout):
        raise URLError("secret-student-information")
    client = CanvasHTTP("https://school.example", "secret", opener=opener, sleeper=lambda _: None)
    try:
        client.get_list("/api/v1/courses")
    except CanvasReadError as exc:
        assert "secret-student-information" not in str(exc)
        assert "saved tasks" in str(exc)
    else:
        assert False


def test_sync_failure_log_is_non_sensitive(caplog):
    def worker():
        raise RuntimeError("SECRET-TOKEN")
    with caplog.at_level(logging.ERROR, logger="synccanvas.reliability"):
        sync = BackgroundSync(worker)
        sync.request_sync()
        assert sync.wait().state == SyncState.ERROR
    assert "sync_failed" in caplog.text
    assert "SECRET-TOKEN" not in caplog.text


def test_health_and_request_id():
    response = TestClient(app).get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}
    assert response.headers.get("X-Request-ID")
