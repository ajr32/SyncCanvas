
"""Tests for Canvas course and assignment mapping."""

import pytest

from synccanvas.services.canvas_mapping import (
    map_assignments,
    map_courses,
    match_course,
    parse_course,
)
from synccanvas.services.canvas_reader import CanvasReadError


def test_valid_course():
    course = parse_course({
        "id": 7,
        "name": "Mathematics 7",
        "course_code": "MATH7",
    })
    assert course.canvas_id == 7
    assert course.name == "Mathematics 7"
    assert course.course_code == "MATH7"


def test_course_code_fallback():
    course = parse_course({"id": 7, "name": "Science"})
    assert course.course_code == "Science"


def test_missing_course_name():
    with pytest.raises(CanvasReadError):
        parse_course({"id": 7})


def test_invalid_course_id():
    with pytest.raises(CanvasReadError):
        parse_course({"id": True, "name": "Science"})


def test_multiple_courses():
    courses = map_courses([
        {"id": 1, "name": "Science"},
        {"id": 2, "name": "Math"},
    ])
    assert len(courses) == 2


def test_duplicate_courses():
    with pytest.raises(CanvasReadError):
        map_courses([
            {"id": 1, "name": "Science"},
            {"id": 1, "name": "Math"},
        ])


def test_assignment_with_due_date():
    result = map_assignments([
        {
            "id": 123,
            "name": "Homework",
            "due_at": "2026-10-20T20:00:00Z",
        }
    ], 7)

    assert result[0].due_date == "2026-10-20"
    assert result[0].source == "canvas"
    assert result[0].course_id == 7


def test_assignment_without_due_date():
    result = map_assignments([
        {"id": 123, "name": "Read chapter 2"}
    ], 7)

    assert result[0].due_at is None
    assert result[0].due_date is None


def test_invalid_due_date():
    with pytest.raises(CanvasReadError):
        map_assignments([
            {"id": 123, "name": "Homework", "due_at": "tomorrow"}
        ], 7)


def test_due_date_requires_timezone():
    with pytest.raises(CanvasReadError):
        map_assignments([
            {
                "id": 123,
                "name": "Homework",
                "due_at": "2026-10-20T20:00:00",
            }
        ], 7)


def test_duplicate_assignments():
    with pytest.raises(CanvasReadError):
        map_assignments([
            {"id": 123, "name": "Homework"},
            {"id": 123, "name": "Homework"},
        ], 7)


def test_explicit_course_match():
    course = parse_course({"id": 7, "name": "Math"})
    assert match_course(course, {7: 42}) == 42


def test_unmatched_course_is_not_guessed():
    course = parse_course({"id": 7, "name": "Math"})
    assert match_course(course, {8: 42}) is None


def test_invalid_planner_class_id():
    course = parse_course({"id": 7, "name": "Math"})
    with pytest.raises(CanvasReadError):
        match_course(course, {7: 0})


def test_empty_lists():
    assert map_courses([]) == []
    assert map_assignments([], 7) == []
