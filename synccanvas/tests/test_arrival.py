
"""Tests for the adult-verified arrival-home checklist."""

from datetime import date, timedelta

import pytest

from synccanvas.database import db
from synccanvas.services.arrival import (
    ARRIVAL_ITEMS,
    arrival_complete,
    get_arrival_checks,
    set_arrival_check,
)


@pytest.fixture
def isolated_arrival_db(tmp_path, monkeypatch):
    import synccanvas.database as storage

    monkeypatch.setattr(
        storage, "DB_PATH", tmp_path / "arrival_test.sqlite3"
    )


def test_new_day_starts_unchecked(isolated_arrival_db):
    day = date(2026, 10, 22)

    items = get_arrival_checks(day)

    assert len(items) == 4
    assert all(not item["verified"] for item in items)
    assert not arrival_complete(day)


def test_verify_and_undo(isolated_arrival_db):
    day = date(2026, 10, 22)

    set_arrival_check("blue_folder", True, day)

    items = get_arrival_checks(day)
    folder = next(
        item for item in items
        if item["key"] == "blue_folder"
    )

    assert folder["verified"]
    assert folder["verified_at"] is not None

    set_arrival_check("blue_folder", False, day)

    items = get_arrival_checks(day)
    folder = next(
        item for item in items
        if item["key"] == "blue_folder"
    )

    assert not folder["verified"]
    assert folder["verified_at"] is None


def test_all_four_required(isolated_arrival_db):
    day = date(2026, 10, 22)

    for key, _ in ARRIVAL_ITEMS[:3]:
        set_arrival_check(key, True, day)

    assert not arrival_complete(day)

    set_arrival_check(ARRIVAL_ITEMS[3][0], True, day)

    assert arrival_complete(day)


def test_new_day_resets_without_losing_history(
    isolated_arrival_db,
):
    yesterday = date(2026, 10, 22)
    today = yesterday + timedelta(days=1)

    for key, _ in ARRIVAL_ITEMS:
        set_arrival_check(key, True, yesterday)

    assert arrival_complete(yesterday)

    assert not arrival_complete(today)
    assert all(
        not item["verified"]
        for item in get_arrival_checks(today)
    )

    assert arrival_complete(yesterday)


def test_invalid_item_rejected(isolated_arrival_db):
    with pytest.raises(ValueError):
        set_arrival_check(
            "not_a_real_item",
            True,
            date(2026, 10, 22),
        )
