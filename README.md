# LLM Evals Scorecard: proving a model's mistake with SQL

A small evaluation toolkit for LLM answers to questions about data. The core idea:
**a model's answer counts as a mistake only if you can prove it with an independent query.**
The repository contains the test suite, the SQL ground truth, an automatic scoring rule,
a SQLite journal for recording and assessing answers, and a report over that journal.
Documents are in Russian.

> Scope: this repository is the *evaluation design and tooling*. It does not contain a
> recorded run of a real model; the journal is created empty (cases and prompts loaded).

## What is inside

**1. Test suite** – [`eval_suite/cases.md`](eval_suite/cases.md), 10 cases over a synthetic
research-station database, covering five quality dimensions:

| Dimension | What it checks | Example trap |
|-----------|----------------|--------------|
| meaning | does the model understand the schema | a false premise: "the leader of experiment 105 was also a participant" (he was not) |
| calculation | is the number right | month boundary: a record at exactly `2026-08-01 00:00:00` is **not** July (10, not 11) |
| missing | known vs. unknown | voltage is `NULL`: the right answer is "unknown", not 0 |
| ambiguity | ask or split instead of guessing | two people named *Alina Orlova* |
| stability | same meaning, two phrasings | `kg` + `g` summed in grams; `COUNT(*)` after a JOIN gives 31 instead of 7 |

Every case stores a proof query and a note on why it is unambiguous. `src/verify_cases.py`
executes all of them. [`eval_suite/rubric.md`](eval_suite/rubric.md) defines pass / fail /
unclear for each dimension; [`eval_suite/warmups.md`](eval_suite/warmups.md) holds the practice questions.

**2. Scoring rule** – [`src/evaluate.py`](src/evaluate.py) checks one numeric claim against
the SQL result with an explicit tolerance and returns `прошёл / не прошёл / спорно` **with a reason**.
Design choices: `True`, strings, `NaN` and `None` are *not* numbers → "unclear" rather than a
silent pass or fail; a corrupted reference value is a problem of the *check*, not an error of the model;
the rule states what it cannot see (wrong reasoning that lands on the right number).

**3. Journal and report** – [`sql/journal_schema.sql`](sql/journal_schema.sql) (cases, prompts, attempts,
pairs, assessments with CHECK constraints), [`sql/report.sql`](sql/report.sql) and [`src/report.py`](src/report.py).
The report counts one unit per assessed answer (one per pair for stability), separates normal and
challenge cases, and prints **"no data"** instead of 0 % when the denominator is zero.
The journal is opened read-only with an SQLite authorizer.

## Run it

Python 3.9+, standard library only.

```bash
python3 src/build_station_db.py        # data/station.db from schema.sql + seed.sql
python3 src/verify_cases.py            # run the proof query of every case
python3 src/init_journal.py            # eval_journal.db with the suite loaded
python3 src/report.py                  # report over the journal
python3 -m unittest discover -s tests -v
```

## Tests (10)

The scoring rule (required cases, Python traps like `True == 1`, rounding tolerance, broken input),
the documented answers of the proof queries (11, 10, 2000 g, 7 vs 31) and the report on a
small synthetic journal, an empty journal and a missing file.

Context: a learning case from the School 21 AI-evaluation day.
