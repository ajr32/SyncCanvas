
"""Tests for #132: deleted and manually edited calendar events.

All Google Calendar interactions are simulated.
"""

from datetime import date, timedelta

from synccanvas.services import google_calendar_export as exporter
from synccanvas.tests.test_google_calendar_export import setup_export


def event_key():
    return ("calendar-7", exporter.event_id(7, 123))


def test_deleted_event_is_recreated(setup_export):
    service, assignment, _ = setup_export

    exporter.export_assignments(service, apply=True)

    # Simulate deletion in Google Calendar.
    del service.fake_events.stored[event_key()]

    result = exporter.export_assignments(service, apply=True)

    assert result.created == 1
    assert result.updated == 0
    assert event_key() in service.fake_events.stored
    assert service.fake_events.insert_calls == 2


def test_manually_edited_title_is_restored(setup_export):
    service, assignment, _ = setup_export

    exporter.export_assignments(service, apply=True)

    service.fake_events.stored[event_key()][
        "summary"
    ] = "My manually changed title"

    result = exporter.export_assignments(service, apply=True)

    assert result.updated == 1
    assert (
        service.fake_events.stored[event_key()]["summary"]
        == "Science homework"
    )
    assert service.fake_events.insert_calls == 1


def test_manually_moved_date_is_restored(setup_export):
    service, assignment, _ = setup_export

    exporter.export_assignments(service, apply=True)

    event = service.fake_events.stored[event_key()]
    event["start"] = {"date": "2030-01-01"}
    event["end"] = {"date": "2030-01-02"}

    result = exporter.export_assignments(service, apply=True)

    assert result.updated == 1
    assert event["start"]["date"] == assignment["calendar_date"]
    assert event["end"]["date"] == (
        date.fromisoformat(assignment["calendar_date"])
        + timedelta(days=1)
    ).isoformat()


def test_preview_does_not_restore_manual_edit(setup_export):
    service, assignment, _ = setup_export

    exporter.export_assignments(service, apply=True)

    service.fake_events.stored[event_key()][
        "summary"
    ] = "Manual title"

    result = exporter.export_assignments(service, apply=False)

    assert result.updated == 1
    assert service.fake_events.stored[event_key()][
        "summary"
    ] == "Manual title"
    assert service.fake_events.patch_calls == 0


def test_preview_does_not_recreate_deleted_event(setup_export):
    service, assignment, _ = setup_export

    exporter.export_assignments(service, apply=True)
    del service.fake_events.stored[event_key()]

    result = exporter.export_assignments(service, apply=False)

    assert result.created == 1
    assert event_key() not in service.fake_events.stored
    assert service.fake_events.insert_calls == 1


def test_unrelated_event_is_not_modified(setup_export):
    service, assignment, _ = setup_export

    unrelated_key = ("calendar-7", "unrelated-event")
    unrelated_event = {
        "id": "unrelated-event",
        "summary": "Family appointment",
        "start": {"date": "2030-01-01"},
        "end": {"date": "2030-01-02"},
    }

    service.fake_events.stored[unrelated_key] = (
        unrelated_event.copy()
    )

    exporter.export_assignments(service, apply=True)
    exporter.export_assignments(service, apply=True)

    assert (
        service.fake_events.stored[unrelated_key]
        == unrelated_event
    )


def test_second_sync_after_restoration_is_unchanged(setup_export):
    service, assignment, _ = setup_export

    exporter.export_assignments(service, apply=True)

    service.fake_events.stored[event_key()][
        "summary"
    ] = "Manual title"

    exporter.export_assignments(service, apply=True)
    result = exporter.export_assignments(service, apply=True)

    assert result.created == 0
    assert result.updated == 0
    assert result.unchanged == 1
