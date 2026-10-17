
"""Validation for student tasks."""

from dataclasses import dataclass


ALLOWED_KINDS = (
    "Homework",
    "Study",
    "Finish Classwork",
    "Prepare for Quiz",
    "Ask Teacher",
)


@dataclass(frozen=True)
class TaskInput:
    class_id: int
    kind: str
    details: str


def validate_task(task: TaskInput) -> TaskInput:
    if task.class_id <= 0:
        raise ValueError("Choose a valid class.")

    if task.kind not in ALLOWED_KINDS:
        raise ValueError("Choose a valid task type.")

    details = task.details.strip()

    if not details:
        raise ValueError("Enter what needs to be done.")

    if len(details) > 300:
        raise ValueError(
            "Task description must be 300 characters or fewer."
        )

    return TaskInput(
        class_id=task.class_id,
        kind=task.kind,
        details=details,
    )


def validate_task_details(
    kind: str,
    details: str,
) -> tuple[str, str]:
    """Validate edits where the class ID is unchanged."""

    if kind not in ALLOWED_KINDS:
        raise ValueError("Choose a valid task type.")

    details = details.strip()

    if not 1 <= len(details) <= 300:
        raise ValueError(
            "Enter a task description (1–300 characters)."
        )

    return kind, details


from datetime import date, time


def validate_deadline(due_date="", due_time="", priority="normal"):
    due_date = (due_date or "").strip()
    due_time = (due_time or "").strip()
    priority = (priority or "normal").strip().lower()
    if priority not in ("normal", "low", "high"):
        raise ValueError("Invalid priority")
    if due_date:
        try:
            if date.fromisoformat(due_date).isoformat() != due_date:
                raise ValueError()
        except ValueError as exc:
            raise ValueError("Invalid due date") from exc
    if due_time:
        if not due_date:
            raise ValueError("Due time requires a due date")
        try:
            if len(due_time) != 5 or time.fromisoformat(due_time).strftime("%H:%M") != due_time:
                raise ValueError()
        except ValueError as exc:
            raise ValueError("Invalid due time") from exc
    return due_date or None, due_time or None, priority
