"""Builds data/station.db (a small synthetic research-station database) from schema.sql + seed.sql.

    python3 src/build_station_db.py
"""
import sqlite3
import sys
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"


def build(path=None, in_memory=False):
    """Create the database. Returns an open connection."""
    con = sqlite3.connect(":memory:" if in_memory else str(path or DATA / "station.db"))
    for name in ("schema.sql", "seed.sql"):
        con.executescript((DATA / name).read_text(encoding="utf-8"))
    con.commit()
    return con


if __name__ == "__main__":
    con = build()
    for (table,) in con.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"):
        print("%s: %d rows" % (table, con.execute("SELECT COUNT(*) FROM " + table).fetchone()[0]))
    sys.exit(0)
