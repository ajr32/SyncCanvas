
"""Tests for Google Calendar export and duplicate prevention.

All Google API calls are simulated. No real calendars are modified.
"""

import sys
import types
from datetime import date, timedelta

import pytest

from synccanvas.services import google_calendar_export as exporter


class FakeHttpError(Exception):
    def __init__(self, status):
        self.resp = types.SimpleNamespace(status=status)
        super().__init__(f"Google API error {status}")


class FakeRequest:
    def __init__(self, action):
        self.action = action

    def execute(self, **kwargs):
        return self.action()


class FakeEvents:
    def __init__(self):
        self.stored = {}
        self.insert_calls = 0
        self.patch_calls = 0
        self.fail_status = None

    def get(self, calendarId, eventId):
        def action():
            if self.fail_status is not None:
                raise FakeHttpError(self.fail_status)

            key = (calendarId, eventId)
            if key not in self.stored:
                raise FakeHttpError(404)

            return dict(self.stored[key])

        return FakeRequest(action)

    def insert(self, calendarId, body):
        def action():
            self.insert_calls += 1
            key = (calendarId, body["id"])
            self.stored[key] = dict(body)
            return dict(body)

        return FakeRequest(action)

    def patch(self, calendarId, eventId, body):
        def action():
            self.patch_calls += 1
            key = (calendarId, eventId)
            self.stored[key].update(body)
            return dict(self.stored[key])

        return FakeRequest(action)


class FakeService:
    def __init__(self):
        self.fake_events = FakeEvents()

    def events(self):
        return self.fake_events


@pytest.fixture
def setup_export(monkeypatch):
    # Allow tests to run without the Google API package installed.
    google_module = types.ModuleType("googleapiclient")
    errors_module = types.ModuleType("googleapiclient.errors")
    errors_module.HttpError = FakeHttpError
    google_module.errors = errors_module

    monkeypatch.setitem(
        sys.modules, "googleapiclient", google_module
    )
    monkeypatch.setitem(
        sys.modules, "googleapiclient.errors", errors_module
    )

    tomorrow = (date.today() + timedelta(days=1)).isoformat()

    assignment = {
        "id": 1,
        "canvas_course_id": 7,
        "canvas_assignment_id": 123,
        "title": "Science homework",
        "completed": 0,
        "due_date": tomorrow,
        "planning_date": None,
        "calendar_date": tomorrow,
        "html_url": "https://example.com/assignment/123",
    }

    rows = [assignment]

    monkeypatch.setattr(
        exporter, "load_assignments", lambda: rows
    )
    monkeypatch.setattr(
        exporter, "find_calendars",
        lambda service: {"7": "calendar-7"},
    )

    return FakeService(), assignment, rows


def test_event_id_is_stable_and_google_compatible():
    first = exporter.event_id(7, 123)
    second = exporter.event_id(7, 123)

    assert first == second
    assert all(char in "0123456789abcdefghijklmnopqrstuv"
               for char in first)


def test_different_assignments_have_different_ids():
    assert exporter.event_id(7, 123) != exporter.event_id(7, 124)
    assert exporter.event_id(7, 123) != exporter.event_id(8, 123)


@pytest.mark.parametrize(
    "course_id,assignment_id",
    [(0, 123), (7, 0), (-1, 123), (7, -1)],
)
def test_invalid_ids_are_rejected(course_id, assignment_id):
    with pytest.raises(ValueError):
        exporter.event_id(course_id, assignment_id)


def test_preview_does_not_create_event(setup_export):
    service, _, _ = setup_export

    summary = exporter.export_assignments(service, apply=False)

    assert summary.created == 1
    assert service.fake_events.insert_calls == 0
    assert service.fake_events.stored == {}


def test_first_sync_creates_event(setup_export):
    service, assignment, _ = setup_export

    summary = exporter.export_assignments(service, apply=True)

    assert summary.created == 1
    assert summary.updated == 0
    assert service.fake_events.insert_calls == 1

    key = ("calendar-7", exporter.event_id(7, 123))
    assert key in service.fake_events.stored
    assert service.fake_events.stored[key]["summary"] == assignment["title"]


def test_second_sync_does_not_duplicate_event(setup_export):
    service, _, _ = setup_export

    first = exporter.export_assignments(service, apply=True)
    second = exporter.export_assignments(service, apply=True)

    assert first.created == 1
    assert second.created == 0
    assert second.updated == 0
    assert second.unchanged == 1
    assert service.fake_events.insert_calls == 1
    assert len(service.fake_events.stored) == 1


def test_changed_assignment_updates_existing_event(setup_export):
    service, assignment, _ = setup_export

    exporter.export_assignments(service, apply=True)

    assignment["title"] = "Updated science homework"

    summary = exporter.export_assignments(service, apply=True)

    assert summary.created == 0
    assert summary.updated == 1
    assert service.fake_events.insert_calls == 1
    assert service.fake_events.patch_calls == 1

    key = ("calendar-7", exporter.event_id(7, 123))
    assert (
        service.fake_events.stored[key]["summary"]
        == "Updated science homework"
    )


def test_missing_calendar_is_skipped(setup_export, monkeypatch):
    service, _, _ = setup_export

    monkeypatch.setattr(
        exporter, "find_calendars", lambda service: {}
    )

    summary = exporter.export_assignments(service, apply=True)

    assert summary.skipped == 1
    assert summary.created == 0
    assert service.fake_events.insert_calls == 0


def test_google_api_error_is_not_treated_as_missing_event(setup_export):
    service, _, _ = setup_export
    service.fake_events.fail_status = 503

    with pytest.raises(FakeHttpError) as error:
        exporter.export_assignments(service, apply=True)

    assert error.value.resp.status == 503
    assert service.fake_events.insert_calls == 0
