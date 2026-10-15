
"""Tests for opt-in Canvas synchronization configuration."""

import pytest

from synccanvas import database
from synccanvas.services.canvas_http import CanvasHTTP
from synccanvas.services.canvas_storage import (
    link_canvas_course,
    load_canvas_assignments,
)
from synccanvas.services.canvas_sync_setup import (
    CanvasConfigurationError,
    build_canvas_coordinator,
)


def settings(**changes):
    values = {
        "SYNCCANVAS_CANVAS_URL": "https://canvas.example.edu",
        "SYNCCANVAS_CANVAS_TOKEN": "test-token",
    }
    values.update(changes)
    return values


def test_missing_settings_rejected():
    with pytest.raises(CanvasConfigurationError):
        build_canvas_coordinator({})


def test_missing_token_rejected():
    with pytest.raises(CanvasConfigurationError):
        build_canvas_coordinator(
            settings(SYNCCANVAS_CANVAS_TOKEN="")
        )


def test_missing_url_rejected():
    with pytest.raises(CanvasConfigurationError):
        build_canvas_coordinator(
            settings(SYNCCANVAS_CANVAS_URL="")
        )


def test_http_url_rejected():
    with pytest.raises(CanvasConfigurationError):
        build_canvas_coordinator(
            settings(
                SYNCCANVAS_CANVAS_URL="http://canvas.example.edu"
            )
        )


def test_valid_configuration_starts_idle():
    coordinator = build_canvas_coordinator(settings())

    assert coordinator.status().state.value == "idle"


def test_configuration_does_not_fetch(monkeypatch):
    calls = []

    def fake_fetch(self, course_id):
        calls.append(course_id)
        return []

    monkeypatch.setattr(
        CanvasHTTP,
        "assignments_for_course",
        fake_fetch,
    )

    build_canvas_coordinator(settings())

    assert calls == []


def test_configured_coordinator_imports(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        database,
        "DB_PATH",
        tmp_path / "configured.sqlite3",
    )

    with database.db() as conn:
        conn.execute(
            "INSERT INTO classes (id, name) VALUES (1, 'Math')"
        )
        link_canvas_course(conn, 7, 1)

    calls = []

    def fake_fetch(self, course_id):
        calls.append(course_id)
        return [
            {"id": 123, "name": "Math homework"}
        ]

    monkeypatch.setattr(
        CanvasHTTP,
        "assignments_for_course",
        fake_fetch,
    )

    coordinator = build_canvas_coordinator(settings())

    coordinator.request_sync()
    result = coordinator.wait(timeout=5)

    assert result.state.value == "success"
    assert calls == [7]

    with database.db() as conn:
        records = load_canvas_assignments(conn, 7)

    assert len(records) == 1
    assert records[0].title == "Math homework"


def test_failed_import_reports_safe_error(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        database,
        "DB_PATH",
        tmp_path / "failure.sqlite3",
    )

    with database.db() as conn:
        conn.execute(
            "INSERT INTO classes (id, name) VALUES (1, 'Math')"
        )
        link_canvas_course(conn, 7, 1)

    def fake_fetch(self, course_id):
        raise RuntimeError("PRIVATE_TEST_TOKEN")

    monkeypatch.setattr(
        CanvasHTTP,
        "assignments_for_course",
        fake_fetch,
    )

    coordinator = build_canvas_coordinator(settings())

    coordinator.request_sync()
    result = coordinator.wait(timeout=5)

    assert result.state.value == "error"
    assert "PRIVATE_TEST_TOKEN" not in result.message


def test_configuration_is_independent_of_default_service():
    from synccanvas.services.sync_coordinator import (
        sync_coordinator,
    )

    configured = build_canvas_coordinator(settings())

    assert configured is not sync_coordinator
    assert configured.status().state.value == "idle"


def test_invalid_url_does_not_expose_token():
    with pytest.raises(CanvasConfigurationError) as error:
        build_canvas_coordinator(
            settings(
                SYNCCANVAS_CANVAS_URL="not-a-url",
                SYNCCANVAS_CANVAS_TOKEN="PRIVATE_TEST_TOKEN",
            )
        )

    assert "PRIVATE_TEST_TOKEN" not in str(error.value)
