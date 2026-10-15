
"""Tests for the read-only Canvas adapter."""

import pytest

from synccanvas.services.canvas_reader import (
    CanvasReadError,
    CanvasReader,
    parse_assignment,
)


def sample_assignment():
    return {
        "id": 123,
        "name": "  Mathematics homework  ",
        "description": "<p>Complete questions 1-10</p>",
        "due_at": "2026-10-20T20:00:00Z",
        "html_url": "https://example.instructure.com/courses/7/assignments/123",
    }


def test_reader_starts_unconfigured():
    reader = CanvasReader()
    assert reader.configured is False


def test_unconfigured_reader_fails_safely():
    with pytest.raises(CanvasReadError, match="not connected"):
        CanvasReader().assignments_for_course(7)


def test_valid_assignment():
    item = parse_assignment(sample_assignment(), 7)

    assert item.canvas_id == 123
    assert item.course_id == 7
    assert item.title == "Mathematics homework"
    assert item.due_at == "2026-10-20T20:00:00Z"


def test_missing_optional_fields():
    item = parse_assignment({"id": 1, "name": "Read chapter 2"}, 7)

    assert item.description == ""
    assert item.due_at is None
    assert item.html_url is None


def test_invalid_course_id():
    with pytest.raises(CanvasReadError):
        CanvasReader(lambda _: []).assignments_for_course(0)


def test_invalid_assignment_id():
    with pytest.raises(CanvasReadError):
        parse_assignment({"id": True, "name": "Homework"}, 7)


def test_missing_assignment_title():
    with pytest.raises(CanvasReadError):
        parse_assignment({"id": 1, "name": "  "}, 7)


def test_invalid_description():
    with pytest.raises(CanvasReadError):
        parse_assignment(
            {"id": 1, "name": "Homework", "description": 42},
            7,
        )


def test_fake_canvas_response():
    requested = []

    def fetch(course_id):
        requested.append(course_id)
        return [sample_assignment()]

    reader = CanvasReader(fetch)

    assert reader.configured is True
    assignments = reader.assignments_for_course(7)

    assert requested == [7]
    assert len(assignments) == 1
    assert assignments[0].canvas_id == 123


def test_empty_course():
    reader = CanvasReader(lambda _: [])
    assert reader.assignments_for_course(7) == []


def test_network_error_is_safe():
    def fetch(_):
        raise RuntimeError("SECRET_CANVAS_TOKEN_123")

    reader = CanvasReader(fetch)

    with pytest.raises(CanvasReadError) as error:
        reader.assignments_for_course(7)

    assert "SECRET_CANVAS_TOKEN_123" not in str(error.value)


def test_invalid_response_type():
    reader = CanvasReader(lambda _: {"assignments": []})

    with pytest.raises(CanvasReadError):
        reader.assignments_for_course(7)


def test_duplicate_assignment_ids():
    reader = CanvasReader(
        lambda _: [sample_assignment(), sample_assignment()]
    )

    with pytest.raises(CanvasReadError, match="duplicate"):
        reader.assignments_for_course(7)
