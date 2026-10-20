"""Runs the independent SQL proof of every case of the eval suite on the station database.

    python3 src/verify_cases.py

A case is only a fair test if its right answer can be shown by a query, so each
case stores that query. This script executes them and prints the results next
to the expected behaviour written in eval_suite/cases.json.
"""
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_station_db import build  # noqa: E402

SUITE = Path(__file__).resolve().parents[1] / "eval_suite" / "cases.json"


def statements(sql):
    buffer = ""
    for char in sql:
        buffer += char
        if char == ";" and sqlite3.complete_statement(buffer):
            yield buffer.strip()
            buffer = ""
    if buffer.strip():
        yield buffer.strip()


def run_proofs(con, cases):
    """Return {case id: [rows of every statement]}; raises on a failing query."""
    return {case["id"]: [con.execute(s).fetchall() for s in statements(case["proof_sql"])]
            for case in cases}


def main():
    cases = json.loads(SUITE.read_text(encoding="utf-8"))
    results = run_proofs(build(in_memory=True), cases)
    for case in cases:
        print("\nCase %d [%s/%s] %s" % (case["id"], case["dimension"], case["kind"], case["title"]))
        for rows in results[case["id"]]:
            print("   ", rows[:4])
    return 0


if __name__ == "__main__":
    sys.exit(main())
