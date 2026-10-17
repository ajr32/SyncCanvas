
"""Bell schedule regression tests."""

from datetime import date as RealDate

from fastapi.testclient import TestClient

from synccanvas import database, pages
from synccanvas.main import app


def test_period_creation_assignment_and_validation(tmp_path, monkeypatch):
    monkeypatch.setattr(
        database,
        "DB_PATH",
        tmp_path / "bell.sqlite3",
    )

    with database.db() as conn:
        conn.execute(
            "INSERT INTO classes(id, name) VALUES(1, 'Math')"
        )

    client = TestClient(app)

    assert client.get("/parent/schedule").status_code == 200

    good = {
        "label": "L",
        "start_time": "11:30",
        "end_time": "12:00",
        "days": ["0", "1", "2", "3", "4"],
    }

    response = client.post(
        "/parent/schedule/add",
        data=good,
        follow_redirects=False,
    )
    assert response.status_code == 303

    with database.db() as conn:
        pid = conn.execute(
            "SELECT id FROM bell_periods WHERE label='L'"
        ).fetchone()["id"]

    response = client.post(
        f"/parent/schedule/{pid}/assign",
        data={"class_ids": "1"},
        follow_redirects=False,
    )
    assert response.status_code == 303

    with database.db() as conn:
        count = conn.execute(
            "SELECT count(*) FROM class_periods"
        ).fetchone()[0]
        assert count == 1

    response = client.post(
        "/parent/schedule/add",
        data={**good, "end_time": "10:00"},
    )
    assert response.status_code == 400

    response = client.post(
        f"/parent/schedule/{pid}/assign",
        data={"class_ids": "999"},
    )
    assert response.status_code == 400

    response = client.post(
        f"/parent/schedule/{pid}/delete",
        follow_redirects=False,
    )
    assert response.status_code == 303

    with database.db() as conn:
        count = conn.execute(
            "SELECT count(*) FROM class_periods"
        ).fetchone()[0]
        assert count == 0


def test_scheduled_classes_sort_before_unscheduled(tmp_path, monkeypatch):
    monkeypatch.setattr(
        database,
        "DB_PATH",
        tmp_path / "order.sqlite3",
    )

    class FakeDate:
        @staticmethod
        def today():
            return RealDate(2026, 10, 19)  # Monday

    monkeypatch.setattr(pages, "date", FakeDate)

    with database.db() as conn:
        conn.execute(
            "INSERT INTO classes(id, name, sort_order) "
            "VALUES(1, 'Unscheduled', 0)"
        )

        conn.execute(
            "INSERT INTO classes(id, name, sort_order) "
            "VALUES(2, 'Scheduled', 1)"
        )

        conn.execute(
            "INSERT INTO bell_periods("
            "id, label, start_time, end_time, weekdays"
            ") VALUES(1, '1', '08:00', '08:50', '01234')"
        )

        conn.execute(
            "INSERT INTO class_periods(class_id, period_id) "
            "VALUES(2, 1)"
        )

        names = [
            row["name"]
            for row in pages.get_active_classes(conn)
        ]

    assert names == ["Scheduled", "Unscheduled"]
