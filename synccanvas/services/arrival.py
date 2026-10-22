
"""Adult-verified arrival-home checklist for SyncCanvas."""

from datetime import date

from synccanvas.database import db


ARRIVAL_ITEMS = (
    ("blue_folder", "Take out blue folder"),
    ("binder", "Take out binder"),
    ("chromebook", "Take out Chromebook and plug it in"),
    ("hebrew", "Take out Hebrew practice materials"),
)


def _ensure_table(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS arrival_checks (
            day TEXT NOT NULL,
            item_key TEXT NOT NULL,
            verified INTEGER NOT NULL DEFAULT 0,
            verified_at TEXT,
            PRIMARY KEY (day, item_key)
        )
        """
    )


def get_arrival_checks(day: date | None = None):
    """Return the four checklist items for a given day."""
    day = day or date.today()

    with db() as conn:
        _ensure_table(conn)

        rows = conn.execute(
            """
            SELECT item_key, verified, verified_at
            FROM arrival_checks
            WHERE day = ?
            """,
            (day.isoformat(),),
        ).fetchall()

    saved = {row["item_key"]: row for row in rows}

    return [
        {
            "key": key,
            "label": label,
            "verified": bool(saved[key]["verified"]) if key in saved else False,
            "verified_at": saved[key]["verified_at"] if key in saved else None,
        }
        for key, label in ARRIVAL_ITEMS
    ]


def set_arrival_check(
    item_key: str,
    verified: bool,
    day: date | None = None,
):
    """Set or clear an adult's verification of an arrival item."""
    valid_keys = {key for key, _ in ARRIVAL_ITEMS}

    if item_key not in valid_keys:
        raise ValueError("Unknown arrival checklist item.")

    day = day or date.today()

    with db() as conn:
        _ensure_table(conn)

        conn.execute(
            """
            INSERT INTO arrival_checks (
                day, item_key, verified, verified_at
            )
            VALUES (?, ?, ?, CASE WHEN ? THEN CURRENT_TIMESTAMP ELSE NULL END)
            ON CONFLICT(day, item_key)
            DO UPDATE SET
                verified = excluded.verified,
                verified_at = excluded.verified_at
            """,
            (
                day.isoformat(),
                item_key,
                int(verified),
                int(verified),
            ),
        )


def arrival_complete(day: date | None = None) -> bool:
    """True only when all four arrival items are verified."""
    return all(item["verified"] for item in get_arrival_checks(day))
