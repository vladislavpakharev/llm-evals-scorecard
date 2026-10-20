"""Отчёт по журналу оценки ответов модели (eval_journal.db).

Запуск из корня репозитория:  python3 src/report.py [путь/к/журналу.db]
По умолчанию читается eval_journal.db (создаётся командой python3 src/init_journal.py).

Программа только читает базу и считает уже поставленные оценки. Запросы лежат в sql/report.sql.
"""
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JOURNAL = ROOT / "eval_journal.db"
REPORT_SQL = ROOT / "sql" / "report.sql"


def readonly(path):
    """Open a database strictly read-only: only SELECT statements are allowed."""
    path = Path(path).resolve()
    if not path.is_file():
        raise FileNotFoundError("Нет файла базы: " + str(path))
    con = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    con.execute("PRAGMA query_only = ON")
    allowed = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ,
               sqlite3.SQLITE_FUNCTION, sqlite3.SQLITE_RECURSIVE}

    def authorize(action, arg1, arg2, db_name, trigger):
        if action == sqlite3.SQLITE_FUNCTION and (arg2 or "").lower() == "load_extension":
            return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK if action in allowed else sqlite3.SQLITE_DENY

    con.set_authorizer(authorize)
    return con
KIND_ORDER = (("normal", "Обычные случаи (одиночные ответы)"),
              ("challenge", "Трудные случаи (одиночные ответы)"),
              ("pair", "Устойчивость (пары ответов)"))
PHASE_NAMES = {"main": "основные (main)", "peer": "обмен (peer)", "defense": "бонус (defense)"}


def load_queries():
    """Читает report.sql и делит его на блоки по строкам '-- name: имя'."""
    text = REPORT_SQL.read_text(encoding="utf-8")
    parts = re.split(r"^-- name: *(\w+) *$", text, flags=re.MULTILINE)
    return {parts[i]: parts[i + 1].strip() for i in range(1, len(parts) - 1, 2)}


def build_sql(queries, name):
    """Для блоков u_... подставляет общую часть units как WITH-запрос."""
    body = queries[name].rstrip(";")
    if name.startswith("u_"):
        return "WITH units AS (\n" + queries["units"].rstrip(";") + "\n)\n" + body
    return body


def fetch(con, queries, name):
    cursor = con.execute(build_sql(queries, name))
    columns = [column[0] for column in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def refs(value):
    return value if value else "-"


def rate_text(failed, passed, rate):
    """Доля ошибок рядом с числом наблюдений; нулевой знаменатель это 'нет данных', а не 0%."""
    observed = failed + passed
    if rate is None:
        return "доля ошибок: нет данных (оценок «прошёл»/«не прошёл»: 0)"
    return "доля ошибок: %d/%d = %.3f (%.1f%%), наблюдений: %d" % (failed, observed, rate, rate * 100, observed)


def marks_text(row, with_refs=True):
    text = "прошёл %d, не прошёл %d, спорно %d, не применимо %d" % (
        row["passed"], row["failed"], row["unclear"], row["na"])
    if with_refs and "pass_refs" in row:
        text += "\n      номера: прошёл [%s]; не прошёл [%s]; спорно [%s]; не применимо [%s]" % (
            refs(row["pass_refs"]), refs(row["fail_refs"]), refs(row["unclear_refs"]), refs(row["na_refs"]))
    return text


def print_report(con, queries):
    print("ОТЧЁТ ПО ЖУРНАЛУ ОЦЕНКИ ОТВЕТОВ МОДЕЛИ")
    print("Основной отчёт: этап main, без сокращённых формулировок, одна основная оценка на ответ,")
    print("устойчивость по парам. Номера: aN = ответ (attempt_id), pN = пара (pair_id).")

    totals = fetch(con, queries, "totals")[0]
    print("\n1. Сколько всего записей")
    print("   Разных случаев: %d [%s]" % (totals["cases_n"], refs(totals["cases_ids"])))
    print("   Формулировок: %d [%s]" % (totals["prompts_n"], refs(totals["prompts_ids"])))
    phases = {row["phase"]: row for row in fetch(con, queries, "attempts_by_phase")}
    total_answers = sum(row["n"] for row in phases.values())
    print("   Ответов всего: %d" % total_answers)
    for phase, title in PHASE_NAMES.items():
        row = phases.get(phase)
        print("     %s: %d [%s]" % (title, row["n"] if row else 0, refs(row["ids"]) if row else "-"))
    print("   Пар ответов: %d [%s]" % (totals["pairs_n"], refs(totals["pairs_ids"])))

    print("\n2 и 3. По сторонам качества (основные оценки)")
    for row in fetch(con, queries, "u_by_dimension"):
        unit = "пары" if row["dimension_id"] == "stability" else "ответы"
        print("   %s (%s), единица счёта: %s" % (row["title"], row["dimension_id"], unit))
        print("      " + marks_text(row))
        print("      " + rate_text(row["failed"], row["passed"], row["fail_rate"]))

    print("\n4. Обычные и трудные случаи раздельно; устойчивость по парам")
    by_kind = {row["kind"]: row for row in fetch(con, queries, "u_by_kind")}
    for kind, title in KIND_ORDER:
        row = by_kind.get(kind)
        if row is None:
            print("   %s: нет данных (оценок нет)" % title)
            continue
        label = "оценённых пар" if kind == "pair" else "оценённых ответов"
        print("   %s: %s: %d" % (title, label, row["total"]))
        print("      " + marks_text(row, with_refs=False))
        print("      " + rate_text(row["failed"], row["passed"], row["fail_rate"]) + "; номера [%s]" % refs(row["refs"]))

    print("\n5. Повторённые вопросы (исходная формулировка, 3 и больше ответов main)")
    repeats = fetch(con, queries, "repeats")
    if not repeats:
        print("   нет данных: ни у одной формулировки нет трёх ответов")
    for row in repeats:
        print("   формулировка %d (случай %d, сторона %s): ответов %d [%s], ошибок %d [%s]; прошёл %d, спорно/не применимо %d, без оценки %d" % (
            row["prompt_id"], row["case_id"], row["dimension_id"], row["answers"], refs(row["attempt_ids"]),
            row["failed"], refs(row["fail_ids"]), row["passed"], row["other"], row["not_assessed"]))
    print("   Сокращённые формулировки (считаются отдельно):")
    shortened = fetch(con, queries, "shortened")
    if not shortened:
        print("      нет данных")
    for row in shortened:
        print("      формулировка %d (случай %d, сторона %s): ответов %d [%s], ошибок %d [%s]; прошёл %d, спорно/не применимо %d, без оценки %d" % (
            row["prompt_id"], row["case_id"], row["dimension_id"], row["answers"], refs(row["attempt_ids"]),
            row["failed"], refs(row["fail_ids"]), row["passed"], row["other"], row["not_assessed"]))

    print("\nОтдельно от основного отчёта")
    extra = fetch(con, queries, "extra_phases")
    if not extra:
        print("   Обмен (peer) и бонус (defense): записей нет")
    for row in extra:
        print("   %s: ответов %d [%s]; прошёл %d, не прошёл %d, спорно %d, не применимо %d, без одиночной оценки %d" % (
            PHASE_NAMES.get(row["phase"], row["phase"]), row["answers"], refs(row["attempt_ids"]),
            row["passed"], row["failed"], row["unclear"], row["na"], row["without_single_mark"]))
    secondary = fetch(con, queries, "secondary")
    if not secondary:
        print("   Дополнительные оценки ответов main: нет")
    for row in secondary:
        print("   Дополнительные оценки по стороне %s: всего %d (прошёл %d, не прошёл %d, спорно %d, не применимо %d) [%s]" % (
            row["dimension_id"], row["total"], row["passed"], row["failed"], row["unclear"], row["na"], refs(row["refs"])))

    print("\nНе вошло в итоги")
    missing = fetch(con, queries, "unassessed")
    if not missing:
        print("   Записей без оценки нет")
    for row in missing:
        print("   %s: %s" % (row["what"], row["ref"]))
    for row in fetch(con, queries, "exclusions"):
        print("   Заметка %d «%s»: %s" % (row["note_id"], row["topic"], row["text_start"].replace("\n", " ")))


def main(argv):
    path = Path(argv[1]) if len(argv) > 1 else JOURNAL
    try:
        con = readonly(path)
    except FileNotFoundError:
        print("Нет файла журнала: %s. Сначала выполни python3 src/init_journal.py" % path)
        return 1
    try:
        print_report(con, load_queries())
    except sqlite3.Error as exc:
        print("Не удалось построить отчёт: %s" % exc)
        return 1
    finally:
        con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
