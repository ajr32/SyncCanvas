
"""Safety and idempotency tests for Canvas reconciliation."""

from dataclasses import replace

import pytest

from synccanvas.services.canvas_mapping import map_assignments
from synccanvas.services.canvas_reconciliation import (
    PlannerAssignment,
    ReconciliationError,
    reconcile_assignments,
)


def incoming(
    assignment_id=123,
    course_id=7,
    name="Math homework",
    due_at="2026-10-20T20:00:00Z",
):
    return map_assignments(
        [{
            "id": assignment_id,
            "name": name,
            "due_at": due_at,
        }],
        course_id,
    )[0]


def existing(**changes):
    record = PlannerAssignment(
        canvas_id=123,
        course_id=7,
        title="Math homework",
        due_at="2026-10-20T20:00:00Z",
        due_date="2026-10-20",
        student_notes="Bring calculator",
        completed=True,
    )
    return replace(record, **changes)


def test_first_import_adds_assignment():
    result = reconcile_assignments([], [incoming()])

    assert result.added_count == 1
    assert result.updated_count == 0
    assert len(result.records) == 1


def test_second_identical_import_is_unchanged():
    first = reconcile_assignments([], [incoming()])
    second = reconcile_assignments(first.records, [incoming()])

    assert second.added_count == 0
    assert second.updated_count == 0
    assert second.unchanged_count == 1


def test_changed_title_updates_canvas_field():
    result = reconcile_assignments(
        [existing()],
        [incoming(name="Updated math homework")],
    )

    assert result.updated_count == 1
    assert result.records[0].title == "Updated math homework"


def test_student_notes_are_preserved():
    result = reconcile_assignments(
        [existing()],
        [incoming(name="New title")],
    )

    assert result.records[0].student_notes == "Bring calculator"


def test_completion_is_preserved():
    result = reconcile_assignments(
        [existing()],
        [incoming(name="New title")],
    )

    assert result.records[0].completed is True


def test_canvas_due_date_can_change():
    result = reconcile_assignments(
        [existing()],
        [incoming(due_at="2026-10-22T20:00:00Z")],
    )

    assert result.records[0].due_date == "2026-10-22"
    assert result.records[0].completed is True


def test_canvas_due_date_can_be_removed():
    result = reconcile_assignments(
        [existing()],
        [incoming(due_at=None)],
    )

    assert result.records[0].due_at is None
    assert result.records[0].due_date is None


def test_different_courses_do_not_collide():
    result = reconcile_assignments(
        [existing()],
        [incoming(assignment_id=123, course_id=8)],
    )

    assert result.added_count == 1
    assert len(result.records) == 2


def test_same_title_different_id_is_new_assignment():
    result = reconcile_assignments(
        [existing()],
        [incoming(assignment_id=456)],
    )

    assert result.added_count == 1
    assert len(result.records) == 2


def test_missing_from_canvas_does_not_delete_record():
    result = reconcile_assignments([existing()], [])

    assert len(result.records) == 1
    assert result.records[0].student_notes == "Bring calculator"


def test_duplicate_incoming_ids_rejected():
    item = incoming()

    with pytest.raises(ReconciliationError, match="Duplicate incoming"):
        reconcile_assignments([], [item, item])


def test_duplicate_existing_ids_rejected():
    record = existing()

    with pytest.raises(ReconciliationError, match="Duplicate existing"):
        reconcile_assignments([record, record], [])


def test_wrong_source_rejected():
    with pytest.raises(ReconciliationError, match="Canvas-linked"):
        reconcile_assignments(
            [existing(source="student")],
            [incoming()],
        )


def test_invalid_import_source_rejected():
    item = replace(incoming(), source="student")

    with pytest.raises(ReconciliationError, match="source"):
        reconcile_assignments([], [item])


def test_input_objects_are_not_modified():
    original = existing()
    imported = incoming(name="New title")

    reconcile_assignments([original], [imported])

    assert original.title == "Math homework"
    assert imported.title == "New title"


def test_mixed_add_update_unchanged():
    unchanged_record = existing()
    changed_record = existing(
        canvas_id=456,
        title="Old science title",
    )

    result = reconcile_assignments(
        [unchanged_record, changed_record],
        [
            incoming(),
            incoming(assignment_id=456, name="New science title"),
            incoming(assignment_id=789, name="History homework"),
        ],
    )

    assert result.added_count == 1
    assert result.updated_count == 1
    assert result.unchanged_count == 1
    assert len(result.records) == 3


def test_repeated_import_is_idempotent_after_update():
    first = reconcile_assignments(
        [existing()],
        [incoming(name="Revised homework")],
    )

    second = reconcile_assignments(
        first.records,
        [incoming(name="Revised homework")],
    )

    assert second.updated_count == 0
    assert second.unchanged_count == 1
    assert second.records == first.records
