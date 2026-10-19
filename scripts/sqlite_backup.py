"""SyncCanvas SQLite backup and safe restore utility. Python standard library only."""
import argparse
from contextlib import closing
import datetime as dt
import os
from pathlib import Path
import sqlite3
import sys
import tempfile

def check_database(path):
    path = Path(path)
    if not path.is_file():
        raise ValueError(f"Database does not exist: {path}")
    # URI mode=ro prevents sqlite3 from silently creating a missing database.
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as conn:
        result = conn.execute("PRAGMA integrity_check").fetchone()[0]
        if result != "ok":
            raise ValueError(f"SQLite integrity check failed: {result}")
        if not conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' LIMIT 1").fetchone():
            raise ValueError("Database has no tables")

def backup(source, directory, keep=14):
    source, directory = Path(source), Path(directory)
    if keep < 1:
        raise ValueError("--keep must be at least 1")
    check_database(source)
    directory.mkdir(parents=True, exist_ok=True)
    # Don't overwrite backups made within the same second.
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    dest = directory / f"synccanvas-{stamp}.sqlite3"
    if dest.resolve() == source.resolve():
        raise ValueError("Source and destination cannot be the same")
    try:
        with closing(sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True)) as src:
            with closing(sqlite3.connect(dest)) as target:
                src.backup(target)
                target.commit()
        check_database(dest)
    except Exception:
        dest.unlink(missing_ok=True)
        raise
    # Only prune our own named backups, after a verified successful backup.
    previous = sorted(directory.glob("synccanvas-*.sqlite3"), reverse=True)
    for old in previous[keep:]:
        old.unlink()
    return dest

def restore(source, destination):
    source, destination = Path(source), Path(destination)
    check_database(source)
    if source.resolve() == destination.resolve():
        raise ValueError("Backup and restore target must differ")
    if destination.exists():
        raise FileExistsError(f"Restore target already exists: {destination}. Choose an unused path.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Atomic publish avoids leaving a partially restored target.
    fd, temp_name = tempfile.mkstemp(prefix=".restore-", suffix=".sqlite3", dir=destination.parent)
    os.close(fd)
    temp = Path(temp_name)
    try:
        with closing(sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True)) as src:
            with closing(sqlite3.connect(temp)) as target:
                src.backup(target)
                target.commit()
        check_database(temp)
        # No overwrite, including in race with another process.
        try:
            os.link(temp, destination)
        except FileExistsError:
            raise FileExistsError(f"Restore target already exists: {destination}")
        temp.unlink()
    finally:
        temp.unlink(missing_ok=True)
    return destination

def main(argv=None):
    parser = argparse.ArgumentParser(description="SyncCanvas SQLite backups. Stop SyncCanvas before switching to a restored database.")
    sub = parser.add_subparsers(dest="command", required=True)
    b = sub.add_parser("backup", help="Create and verify a consistent backup, then rotate old backups")
    b.add_argument("--db", default=os.environ.get("SYNCCANVAS_DB", "synccanvas_local.sqlite3"))
    b.add_argument("--dir", default="backups")
    b.add_argument("--keep", type=int, default=14)
    v = sub.add_parser("verify", help="Verify integrity of an existing backup")
    v.add_argument("file")
    r = sub.add_parser("restore", help="Restore into a NEW path; never overwrite the live database")
    r.add_argument("file")
    r.add_argument("--to", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "backup":
            print(f"Backup created and verified: {backup(args.db, args.dir, args.keep)}")
        elif args.command == "verify":
            check_database(args.file)
            print(f"Backup verified: {args.file}")
        else:
            print(f"Restored and verified: {restore(args.file, args.to)}")
            print("Stop SyncCanvas before manually swapping this restored database into service.")
        return 0
    except (OSError, ValueError, sqlite3.DatabaseError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
