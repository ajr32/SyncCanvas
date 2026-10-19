"""Canvas integration regression checks; no live Canvas credentials required."""
from synccanvas.services.canvas_reader import parse_assignment
from synccanvas.services.canvas_mapping import map_assignments
from synccanvas.services.canvas_reconciliation import reconcile_assignments
from synccanvas.services.canvas_course_discovery import discover_courses
from synccanvas.services.canvas_http import CanvasHTTP
from synccanvas.services.canvas_reader import CanvasReadError
import pytest


def test_missing_submission_is_not_completed():
    raw = {"id": 1, "name": "Quiz", "submission": {"missing": True, "workflow_state": "unsubmitted"}}
    mapped = map_assignments([raw], 12)[0]
    assert mapped.canvas_missing is True
    assert mapped.canvas_submitted is False
    result = reconcile_assignments([], [mapped])
    assert result.added[0].canvas_missing is True
    assert result.added[0].completed is False


def test_submitted_work_is_not_missing_even_if_canvas_flag_is_stale():
    raw = {"id": 1, "name": "Quiz", "submission": {"missing": True, "workflow_state": "submitted"}}
    item = parse_assignment(raw, 12)
    assert item.canvas_submitted is True
    assert item.canvas_missing is False


def test_missing_field_absent_is_not_assumed_missing():
    assert parse_assignment({"id": 1, "name": "Reference"}, 12).canvas_missing is False


def test_course_rename_keeps_stable_canvas_identity():
    old = discover_courses(lambda: [{"id": 77, "name": "Math"}])
    renamed = discover_courses(lambda: [{"id": 77, "name": "Algebra", "workflow_state": "completed"}])
    assert old[0].canvas_course_id == renamed[0].canvas_course_id
    assert renamed[0].name == "Algebra"
    assert renamed[0].workflow_state == "completed"


def test_canvas_client_requires_https_and_token():
    with pytest.raises(ValueError):
        CanvasHTTP("http://canvas.example.org", "token")
    with pytest.raises(ValueError):
        CanvasHTTP("https://canvas.example.org", "")


def test_canvas_rejects_unsafe_pagination_target():
    client = CanvasHTTP("https://canvas.example.org", "token")
    with pytest.raises(CanvasReadError):
        client._validate_url("https://other.example.org/api/v1/courses")
