
"""Tests for parent-controlled class management."""

import pytest

from synccanvas import database
from synccanvas.services.class_management import (
    ClassManagementError,
    active_classes,
    add_class,
    delete_empty_class,
    list_classes,
    rename_class,
    set_archived,
    set_enabled,
)


@pytest.fixture
def connection(tmp_path, monkeypatch):
    monkeypatch.setattr(
        database,
        "DB_PATH",
        tmp_path / "class_management.sqlite3",
    )

    with database.db() as conn:
        yield conn


def test_add_class(connection):
    class_id = add_class(connection, "Mathematics 7")

    classes = list_classes(connection)

    assert len(classes) == 1
    assert classes[0].id == class_id
    assert classes[0].name == "Mathematics 7"


def test_new_class_enabled_by_default(connection):
    add_class(connection, "Science II")

    classes = active_classes(connection)

    assert len(classes) == 1
    assert classes[0].name == "Science II"


def test_disable_hides_without_deleting(connection):
    class_id = add_class(connection, "Student Resources")

    set_enabled(connection, class_id, False)

    assert active_classes(connection) == []
    assert len(list_classes(connection)) == 1


def test_archive_hides_without_deleting(connection):
    class_id = add_class(connection, "Physical Education Q1")

    set_archived(connection, class_id, True)

    assert active_classes(connection) == []
    assert list_classes(connection)[0].archived


def test_reenable_archived_class_stays_hidden(connection):
    class_id = add_class(connection, "Physical Education Q1")

    set_archived(connection, class_id, True)
    set_enabled(connection, class_id, True)

    assert active_classes(connection) == []


def test_restore_class(connection):
    class_id = add_class(connection, "Science II")

    set_enabled(connection, class_id, False)
    set_archived(connection, class_id, True)

    set_archived(connection, class_id, False)
    set_enabled(connection, class_id, True)

    assert len(active_classes(connection)) == 1


def test_rename_class(connection):
    class_id = add_class(connection, "Math")

    rename_class(connection, class_id, "Mathematics 7")

    assert list_classes(connection)[0].name == "Mathematics 7"


def test_duplicate_name_rejected(connection):
    add_class(connection, "Math")

    with pytest.raises(ClassManagementError):
        add_class(connection, "Math")


def test_delete_empty_class(connection):
    class_id = add_class(connection, "string")

    delete_empty_class(connection, class_id)

    assert list_classes(connection) == []


def test_cannot_delete_class_with_task(connection):
    class_id = add_class(connection, "Math")

    connection.execute(
        """
        INSERT INTO entries(class_id, kind, details)
        VALUES (?, 'Homework', 'Questions 1–10')
        """,
        (class_id,),
    )

    with pytest.raises(ClassManagementError):
        delete_empty_class(connection, class_id)


def test_cannot_delete_class_with_checkin(connection):
    class_id = add_class(connection, "Math")

    connection.execute(
        """
        INSERT INTO checkins(class_id, day)
        VALUES (?, '2026-10-15')
        """,
        (class_id,),
    )

    with pytest.raises(ClassManagementError):
        delete_empty_class(connection, class_id)


def test_cannot_delete_linked_class(connection):
    class_id = add_class(connection, "Math")

    connection.execute(
        """
        INSERT INTO canvas_course_links(
            canvas_course_id, class_id
        )
        VALUES (12345, ?)
        """,
        (class_id,),
    )

    with pytest.raises(ClassManagementError):
        delete_empty_class(connection, class_id)


def test_missing_class_rejected(connection):
    with pytest.raises(ClassManagementError):
        set_enabled(connection, 9999, False)
