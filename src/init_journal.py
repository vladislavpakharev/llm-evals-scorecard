"""Creates eval_journal.db: the evaluation journal with the suite already loaded.

    python3 src/init_journal.py

Loads sql/journal_schema.sql and the cases and prompts from eval_suite/cases.json.
Model answers (attempts) and their assessments are added later; src/report.py
summarises whatever the journal contains.
"""
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def create(path):
    con = sqlite3.connect(str(path))
    con.executescript((ROOT / "sql" / "journal_schema.sql").read_text(encoding="utf-8"))
    cases = json.loads((ROOT / "eval_suite" / "cases.json").read_text(encoding="utf-8"))
    prompt_id = 0
    for case in cases:
        con.execute("INSERT INTO cases (case_id, dimension_id, kind, title, expected, proof_sql, proof_reason) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (case["id"], case["dimension"], case["kind"], case["title"],
                     case["expected"], case["proof_sql"], case["proof_reason"]))
        for prompt in case["prompts"]:
            prompt_id += 1
            con.execute("INSERT INTO prompts (prompt_id, case_id, label, text) VALUES (?, ?, ?, ?)",
                        (prompt_id, case["id"], prompt["label"], prompt["text"]))
    con.commit()
    return con


if __name__ == "__main__":
    target = ROOT / "eval_journal.db"
    if target.exists():
        print("%s already exists, not overwritten" % target.name)
        sys.exit(1)
    connection = create(target)
    print("created %s: %d cases, %d prompts" % (
        target.name,
        connection.execute("SELECT COUNT(*) FROM cases").fetchone()[0],
        connection.execute("SELECT COUNT(*) FROM prompts").fetchone()[0]))
