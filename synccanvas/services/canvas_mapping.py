"""Validated, read-only Canvas course and assignment mapping.

Canvas owns imported school data. Student-entered planner tasks are unchanged.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Mapping
from synccanvas.services.canvas_reader import CanvasAssignment, CanvasReadError, parse_assignment
from synccanvas.services.family_time import canvas_due_date

@dataclass(frozen=True)
class CanvasCourse:
    canvas_id: int
    name: str
    course_code: str

@dataclass(frozen=True)
class MappedAssignment:
    canvas_id: int
    course_id: int
    title: str
    description: str
    due_at: str | None
    due_date: str | None
    html_url: str | None
    source: str = "canvas"
    submission_types: tuple[str, ...] = ()
    canvas_submitted: bool = False
    canvas_missing: bool = False

def _id(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise CanvasReadError("Invalid Canvas identifier.")
    return value

def parse_course(raw: Mapping[str, Any]) -> CanvasCourse:
    if not isinstance(raw, Mapping):
        raise CanvasReadError("Invalid Canvas course.")
    canvas_id = _id(raw.get("id"))
    name = raw.get("name")
    if not isinstance(name, str) or not name.strip():
        raise CanvasReadError("Canvas course has no name.")
    code = raw.get("course_code")
    if code is None:
        code = name
    if not isinstance(code, str):
        raise CanvasReadError("Invalid Canvas course code.")
    return CanvasCourse(canvas_id=canvas_id, name=name.strip(), course_code=code.strip() or name.strip())

def map_courses(raw_courses: list[dict]) -> list[CanvasCourse]:
    if not isinstance(raw_courses, list):
        raise CanvasReadError("Invalid Canvas course list.")
    courses = [parse_course(raw) for raw in raw_courses]
    ids = [course.canvas_id for course in courses]
    if len(ids) != len(set(ids)):
        raise CanvasReadError("Duplicate Canvas course identifiers.")
    return courses

def _due_date(value: str | None) -> str | None:
    try:
        return canvas_due_date(value)
    except ValueError as exc:
        raise CanvasReadError(str(exc)) from exc

def map_assignment(assignment: CanvasAssignment) -> MappedAssignment:
    return MappedAssignment(
        canvas_id=assignment.canvas_id, course_id=assignment.course_id,
        title=assignment.title, description=assignment.description,
        due_at=assignment.due_at, due_date=_due_date(assignment.due_at),
        html_url=assignment.html_url, submission_types=assignment.submission_types,
        canvas_submitted=assignment.canvas_submitted,
        canvas_missing=assignment.canvas_missing,
    )

def map_assignments(raw_assignments: list[dict], course_id: int) -> list[MappedAssignment]:
    _id(course_id)
    if not isinstance(raw_assignments, list):
        raise CanvasReadError("Invalid Canvas assignment list.")
    mapped = [map_assignment(parse_assignment(raw, course_id)) for raw in raw_assignments]
    ids = [assignment.canvas_id for assignment in mapped]
    if len(ids) != len(set(ids)):
        raise CanvasReadError("Duplicate Canvas assignments.")
    return mapped

def match_course(course: CanvasCourse, planner_classes: Mapping[int, int]) -> int | None:
    if not isinstance(planner_classes, Mapping):
        raise CanvasReadError("Invalid planner class mapping.")
    planner_id = planner_classes.get(course.canvas_id)
    return None if planner_id is None else _id(planner_id)
