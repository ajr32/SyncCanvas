
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
