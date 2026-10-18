"""Create a fictional demo database, separate from normal planner data."""
from __future__ import annotations

import argparse
from pathlib import Path
from synccanvas import database


def create_demo(path: Path) -> Path:
    path = Path(path).expanduser().resolve()
    if path == database.DB_PATH.expanduser().resolve():
        raise ValueError("Cannot use the family database for demo data")
    if path.exists():
        raise FileExistsError(str(path))
    if not path.parent.is_dir():
        raise ValueError("Output directory does not exist")
    previous = database.DB_PATH
    database.DB_PATH = path
    try:
        with database.db() as conn:
            conn.executemany(
                "INSERT INTO classes(name,sort_order) VALUES (?,?)",
                [("Demo Math", 1), ("Demo Science", 2)],
            )
            ids = {
                r["name"]: r["id"]
                for r in conn.execute("SELECT id,name FROM classes")
            }
            conn.executemany(
                "INSERT INTO entries(class_id,kind,details,origin,progress) "
                "VALUES (?,?,?,'student',?)",
                [
                    (
                        ids["Demo Math"],
                        "Homework",
                        "Practice problems 1-5",
                        "not_started",
                    ),
                    (
                        ids["Demo Science"],
                        "Study",
                        "Review sample vocabulary",
                        "in_progress",
                    ),
                ],
            )
    finally:
        database.DB_PATH = previous
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("synccanvas_demo.sqlite3"),
    )
    args = parser.parse_args()
    try:
        print(create_demo(args.output))
    except (ValueError, FileExistsError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()