"""Run: python -m unittest discover -s synccanvas/tests -p test_family_time.py"""
import os
import unittest
from datetime import datetime, timezone
from unittest.mock import patch
from synccanvas.services.family_time import family_today, canvas_due_date

class FamilyTimeTests(unittest.TestCase):
    def test_local_midnight_and_dst(self):
        with patch.dict(os.environ, {"SYNCCANVAS_TIMEZONE": "America/New_York"}):
            self.assertEqual(family_today(datetime(2026, 3, 8, 4, 30, tzinfo=timezone.utc)).isoformat(), "2026-03-07")
            self.assertEqual(family_today(datetime(2026, 3, 8, 7, 30, tzinfo=timezone.utc)).isoformat(), "2026-03-08")
            self.assertEqual(canvas_due_date("2026-11-01T04:30:00Z"), "2026-11-01")
            self.assertEqual(canvas_due_date("2026-11-01T03:30:00Z"), "2026-10-31")
            self.assertEqual(canvas_due_date("2026-03-08T06:30:00+00:00"), "2026-03-08")
    def test_bad_input(self):
        with patch.dict(os.environ, {"SYNCCANVAS_TIMEZONE": "America/New_York"}):
            with self.assertRaises(ValueError): canvas_due_date("2026-03-08T10:00:00")
            with self.assertRaises(ValueError): canvas_due_date("not-a-date")
            with self.assertRaises(ValueError): family_today(datetime(2026, 1, 1))
    def test_invalid_zone(self):
        with patch.dict(os.environ, {"SYNCCANVAS_TIMEZONE": "Not/AZone"}):
            with self.assertRaises(ValueError): family_today()

if __name__ == "__main__": unittest.main()
