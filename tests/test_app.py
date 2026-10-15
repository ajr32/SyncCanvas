
"""Integration tests for the SyncCanvas family planner."""

import pytest
from fastapi.testclient import TestClient

from synccanvas import database, main


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Give each test its own temporary SQLite database."""
    monkeypatch.setattr(
        database,
        "DB_PATH",
        tmp_path / "test.sqlite3",
    )

    with TestClient(main.app) as test_client:
        yield test_client


def test_student_to_parent_flow(client):
    # Student opens the planner.
    response = client.get("/")
    assert response.status_code == 200

    # Student adds a class.
    response = client.post(
        "/classes",
        data={"name": "Math"},
    )
    assert response.status_code == 200

    # Student records homework.
    response = client.post(
        "/classes/1/entries",
        data={
            "kind": "Homework",
            "details": "Page 12",
        },
    )
    assert response.status_code == 200

    # Parent can see the unfinished assignment.
    parent = client.get("/parent")
    assert parent.status_code == 200
    assert "Math" in parent.text
    assert "Page 12" in parent.text
    assert "unfinished tasks" in parent.text

    # Student marks the assignment done.
    response = client.post("/entries/1/toggle")
    assert response.status_code == 200

    parent = client.get("/parent")
    assert "Student says done" in parent.text

    # Parent confirms completion.
    response = client.post(
        "/parent/entries/1/confirm"
    )
    assert response.status_code == 200

    parent = client.get("/parent")
    assert "Parent confirmed" in parent.text


def test_parent_returns_task_for_another_look(client):
    client.post(
        "/classes",
        data={"name": "Science"},
    )

    client.post(
        "/classes/1/entries",
        data={
            "kind": "Study",
            "details": "Review chapter 4",
        },
    )

    # Student says the task is complete.
    client.post("/entries/1/toggle")

    # Parent sends it back.
    response = client.post(
        "/parent/entries/1/return"
    )
    assert response.status_code == 200

    # It should reappear in the open task list.
    home = client.get("/home")
    assert home.status_code == 200
    assert "Review chapter 4" in home.text


def test_invalid_and_missing_class(client):
    client.post(
        "/classes",
        data={"name": "Science"},
    )

    # Invalid task type.
    response = client.post(
        "/classes/1/entries",
        data={
            "kind": "Not a real type",
            "details": "Test assignment",
        },
    )
    assert response.status_code == 422

    # Missing required description.
    response = client.post(
        "/classes/1/entries",
        data={"kind": "Study"},
    )
    assert response.status_code == 422

    # Valid task submitted to nonexistent class.
    response = client.post(
        "/classes/99/entries",
        data={
            "kind": "Study",
            "details": "Read chapter 3",
        },
    )
    assert response.status_code == 404

    # Parent cannot confirm an unfinished task.
    response = client.post(
        "/classes/1/entries",
        data={
            "kind": "Homework",
            "details": "Worksheet",
        },
    )
    assert response.status_code == 200

    response = client.post(
        "/parent/entries/1/confirm"
    )
    assert response.status_code == 409


def test_html_is_escaped(client):
    client.post(
        "/classes",
        data={"name": "Science"},
    )

    response = client.post(
        "/classes/1/entries",
        data={
            "kind": "Homework",
            "details": "<script>alert(1)</script>",
        },
    )
    assert response.status_code == 200

    page = client.get("/")

    assert page.status_code == 200
    assert "<script>alert(1)</script>" not in page.text
    assert "&lt;script&gt;" in page.text
