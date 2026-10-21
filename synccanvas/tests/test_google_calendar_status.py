
"""Tests for #131: calendar date and completion updates."""

from datetime import date, timedelta

from synccanvas.services import google_calendar_export as exporter

from synccanvas.tests.test_google_calendar_export import (
    FakeService,
    setup_export,
)


def test_completed_assignment_gets_checkmark(setup_export):
    service, assignment, _ = setup_export

    assignment["completed"] = 1

    summary = exporter.export_assignments(service, apply=True)

    key = ("calendar-7", exporter.event_id(7, 123))
    event = service.fake_events.stored[key]

    assert summary.created == 1
    assert event["summary"] == "\u2713 Science homework"


def test_marking_done_updates_existing_event(setup_export):
    service, assignment, _ = setup_export

    assignment["completed"] = 0
    exporter.export_assignments(service, apply=True)

    assignment["completed"] = 1
    summary = exporter.export_assignments(service, apply=True)

    key = ("calendar-7", exporter.event_id(7, 123))

    assert summary.created == 0
    assert summary.updated == 1
    assert service.fake_events.stored[key]["summary"].startswith(
        "\u2713 "
    )
    assert service.fake_events.insert_calls == 1
    assert service.fake_events.patch_calls == 1


def test_marking_not_done_removes_checkmark(setup_export):
    service, assignment, _ = setup_export

    assignment["completed"] = 1
    exporter.export_assignments(service, apply=True)

    assignment["completed"] = 0
    summary = exporter.export_assignments(service, apply=True)

    key = ("calendar-7", exporter.event_id(7, 123))

    assert summary.updated == 1
    assert service.fake_events.stored[key]["summary"] == (
        "Science homework"
    )
    assert len(service.fake_events.stored) == 1


def test_planning_date_moves_existing_event(setup_export):
    service, assignment, _ = setup_export

    assignment["completed"] = 0
    exporter.export_assignments(service, apply=True)

    new_date = (date.today() + timedelta(days=5)).isoformat()

    assignment["planning_date"] = new_date
    assignment["calendar_date"] = new_date

    summary = exporter.export_assignments(service, apply=True)

    key = ("calendar-7", exporter.event_id(7, 123))
    event = service.fake_events.stored[key]

    assert summary.created == 0
    assert summary.updated == 1
    assert event["start"]["date"] == new_date
    assert len(service.fake_events.stored) == 1


def test_repeated_sync_after_completion_is_unchanged(setup_export):
    service, assignment, _ = setup_export

    assignment["completed"] = 1

    exporter.export_assignments(service, apply=True)
    summary = exporter.export_assignments(service, apply=True)

    assert summary.created == 0
    assert summary.updated == 0
    assert summary.unchanged == 1
    assert service.fake_events.insert_calls == 1


def test_preview_of_status_change_does_not_write(setup_export):
    service, assignment, _ = setup_export

    assignment["completed"] = 0
    exporter.export_assignments(service, apply=True)

    assignment["completed"] = 1
    summary = exporter.export_assignments(service, apply=False)

    key = ("calendar-7", exporter.event_id(7, 123))

    assert summary.updated == 1
    assert service.fake_events.patch_calls == 0
    assert service.fake_events.stored[key]["summary"] == (
        "Science homework"
    )
