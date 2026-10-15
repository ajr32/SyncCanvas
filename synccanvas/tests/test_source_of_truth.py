"""Tests for SyncCanvas source-of-truth rules."""

import unittest

from synccanvas.services.source_of_truth import (
    DataSource,
    SourceConflictError,
    UnknownFieldError,
    can_update,
    get_field_owner,
    resolve_update,
)


class TestSourceOfTruth(unittest.TestCase):

    def test_canvas_owns_assignment_due_date(self):
        self.assertEqual(
            get_field_owner("assignment_due_date"),
            DataSource.CANVAS,
        )

    def test_synccanvas_owns_student_notes(self):
        self.assertEqual(
            get_field_owner("student_notes"),
            DataSource.SYNCCANVAS,
        )

    def test_canvassync_owns_calendar_event_id(self):
        self.assertEqual(
            get_field_owner("google_calendar_event_id"),
            DataSource.CANVASSYNC,
        )

    def test_canvas_can_update_due_date(self):
        self.assertTrue(
            can_update("assignment_due_date", "canvas")
        )

    def test_synccanvas_cannot_update_due_date(self):
        self.assertFalse(
            can_update("assignment_due_date", "synccanvas")
        )

    def test_authorized_update(self):
        result = resolve_update(
            field="assignment_due_date",
            current_value="2026-10-15",
            new_value="2026-10-16",
            source=DataSource.CANVAS,
        )
        self.assertEqual(result, "2026-10-16")

    def test_unauthorized_update(self):
        with self.assertRaises(SourceConflictError):
            resolve_update(
                field="assignment_due_date",
                current_value="2026-10-15",
                new_value="2026-10-16",
                source=DataSource.SYNCCANVAS,
            )

    def test_unknown_field(self):
        with self.assertRaises(UnknownFieldError):
            get_field_owner("mystery_field")

    def test_unknown_source(self):
        self.assertFalse(
            can_update("student_notes", "unknown_system")
        )

    def test_empty_value_is_allowed(self):
        result = resolve_update(
            field="student_notes",
            current_value="Old note",
            new_value="",
            source=DataSource.SYNCCANVAS,
        )
        self.assertEqual(result, "")

    def test_none_value_is_allowed(self):
        result = resolve_update(
            field="assignment_due_date",
            current_value="2026-10-15",
            new_value=None,
            source=DataSource.CANVAS,
        )
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
