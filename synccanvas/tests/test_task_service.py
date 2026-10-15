
import pytest

from synccanvas.services.tasks import (
    TaskInput,
    validate_task,
)


def test_valid_homework():
    task = TaskInput(
        class_id=1,
        kind="Homework",
        details="  Finish math worksheet  ",
    )

    result = validate_task(task)

    assert result.details == "Finish math worksheet"
    assert result.kind == "Homework"


def test_empty_description():
    task = TaskInput(
        class_id=1,
        kind="Homework",
        details="   ",
    )

    with pytest.raises(ValueError):
        validate_task(task)


def test_invalid_class():
    task = TaskInput(
        class_id=0,
        kind="Study",
        details="Study chapter 3",
    )

    with pytest.raises(ValueError):
        validate_task(task)


def test_invalid_task_type():
    task = TaskInput(
        class_id=1,
        kind="Unknown",
        details="Something",
    )

    with pytest.raises(ValueError):
        validate_task(task)
