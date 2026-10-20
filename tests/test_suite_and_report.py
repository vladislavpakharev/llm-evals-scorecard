import contextlib
import io
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import build_station_db  # noqa: E402
import init_journal  # noqa: E402
import report  # noqa: E402
import verify_cases  # noqa: E402

CASES = json.loads((ROOT / "eval_suite" / "cases.json").read_text(encoding="utf-8"))


class SuiteTests(unittest.TestCase):
    def test_suite_shape(self):
        self.assertEqual(len(CASES), 10)
        self.assertEqual({c["dimension"] for c in CASES},
                         {"meaning", "calculation", "missing", "ambiguity", "stability"})
        self.assertTrue(all(c["proof_sql"].strip() for c in CASES))
        # stability cases are pairs of two phrasings of one question
        for case in CASES:
            if case["kind"] == "pair":
                self.assertEqual(len(case["prompts"]), 2)

    def test_proof_sql_gives_the_documented_answers(self):
        proofs = verify_cases.run_proofs(build_station_db.build(in_memory=True), CASES)
        self.assertEqual(proofs[3][0], [(11,)])        # valid measurements
        self.assertEqual(proofs[4][0], [(10,)])        # July, month boundary excluded
        self.assertEqual(proofs[9][1], [(2000.0,)])    # kg and g added in grams
        self.assertEqual(proofs[10][0], [(7,)])        # distinct experiments ...
        self.assertEqual(proofs[10][1], [(31,)])       # ... vs. rows after the JOIN


class ReportTests(unittest.TestCase):
    def make_journal(self, folder):
        path = Path(folder) / "journal.db"
        con = init_journal.create(path)
        # Case 3 (calculation, normal): prompt 3. One right and one wrong answer, assessed.
        for response, verdict in (("11", "pass"), ("12", "fail")):
            cursor = con.execute(
                "INSERT INTO attempts (prompt_id, model, conditions, phase, context_text, "
                "response_text, execution_result) VALUES (3, 'm', 'c', 'main', '', ?, '')", (response,))
            con.execute("INSERT INTO assessments (attempt_id, dimension_id, verdict, reason, assessed_by) "
                        "VALUES (?, 'calculation', ?, 'r', 'me')", (cursor.lastrowid, verdict))
        con.commit()
        con.close()
        return path

    def run_report(self, path):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = report.main(["report.py", str(path)])
        return code, out.getvalue()

    def test_report_counts_assessed_answers_and_error_rate(self):
        with tempfile.TemporaryDirectory() as folder:
            code, text = self.run_report(self.make_journal(folder))
        self.assertEqual(code, 0)
        self.assertIn("Ответов всего: 2", text)
        self.assertIn("прошёл 1, не прошёл 1", text)
        self.assertIn("доля ошибок: 1/2 = 0.500", text)

    def test_empty_journal_says_no_data_instead_of_zero_percent(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "empty.db"
            init_journal.create(path).close()
            code, text = self.run_report(path)
        self.assertEqual(code, 0)
        self.assertIn("нет данных", text)
        self.assertNotIn("0.0%", text)

    def test_missing_journal_is_reported(self):
        code, text = self.run_report("/no/such/journal.db")
        self.assertEqual(code, 1)
        self.assertIn("Нет файла журнала", text)

    def test_report_database_is_opened_read_only(self):
        with tempfile.TemporaryDirectory() as folder:
            con = report.readonly(self.make_journal(folder))
            with self.assertRaises(sqlite3.DatabaseError):
                con.execute("DELETE FROM cases")


if __name__ == "__main__":
    unittest.main()
