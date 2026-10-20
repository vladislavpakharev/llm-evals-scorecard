"""Проверки правила src/evaluate.py.

Запуск из корня репозитория: python3 -m unittest discover -s tests

Все числа в этом файле придуманы мной заранее, чтобы проверить само правило.
Это не ответы модели, поэтому каждый случай помечен origin = "synthetic_fixture".
Ожидаемую отметку и причину я записал до запуска правила.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from evaluate import evaluate  # noqa: E402

# Три обязательных случая. Тема: сколько записей измерений приходится на июль 2026.
# Правильное число я получил своим SQL: 10 (запись 1010 с временем 2026-08-01 00:00:00 в июль не входит).
CORRECT = {
    "id": "my_correct", "origin": "synthetic_fixture",
    "expected": 10, "claim": 10,
    "expected_mark": "прошёл",
    "reason": "Число из ответа совпало с моим SQL: 10 и 10.",
}
WRONG = {
    "id": "my_wrong", "origin": "synthetic_fixture",
    "expected": 10, "claim": 11,
    "expected_mark": "не прошёл",
    "reason": "11 получается, если ошибочно включить границу 1 августа 00:00:00.",
}
UNCLEAR = {
    "id": "my_unclear", "origin": "synthetic_fixture",
    "expected": 10, "claim": None,
    "expected_mark": "спорно",
    "reason": "Числа в ответе нет. Это не доказывает, что модель ошиблась.",
}

# Дополнительные случаи на ловушки Python и на допуск.
EXTRA = [
    {"id": "my_zero", "origin": "synthetic_fixture", "expected": 0, "claim": 0,
     "expected_mark": "прошёл", "reason": "Ноль это настоящее число, а не отсутствие ответа."},
    {"id": "my_bool", "origin": "synthetic_fixture", "expected": 1, "claim": True,
     "expected_mark": "спорно", "reason": "True равно 1, но булево значение числом не считаем."},
    {"id": "my_string", "origin": "synthetic_fixture", "expected": 10, "claim": "10",
     "expected_mark": "спорно", "reason": "Строка это не число."},
    {"id": "my_nan", "origin": "synthetic_fixture", "expected": 10, "claim": float("nan"),
     "expected_mark": "спорно", "reason": "NaN не конечное число."},
    {"id": "my_rounded_ok", "origin": "synthetic_fixture", "expected": 15.0, "claim": 15.04, "tolerance": 0.05,
     "expected_mark": "прошёл", "reason": "Среднее округлено, разница 0.04 меньше допуска 0.05."},
    {"id": "my_rounded_strict", "origin": "synthetic_fixture", "expected": 15.0, "claim": 15.04,
     "expected_mark": "не прошёл", "reason": "Допуск не задан, поэтому сравнение строгое."},
]

ALL_MINE = [CORRECT, WRONG, UNCLEAR] + EXTRA


class RuleTests(unittest.TestCase):
    def test_three_required_cases(self):
        for case in (CORRECT, WRONG, UNCLEAR):
            self.assertEqual(evaluate(case)["mark"], case["expected_mark"], case["id"])

    def test_extra_cases(self):
        for case in EXTRA:
            with self.subTest(case=case["id"]):
                self.assertEqual(evaluate(case)["mark"], case["expected_mark"], case["reason"])

    def test_reason_is_never_empty(self):
        for case in ALL_MINE:
            with self.subTest(case=case["id"]):
                self.assertNotEqual(evaluate(case)["reason"].strip(), "")

    def test_broken_input_is_unclear_not_a_crash(self):
        for broken in (None, "text", {}, {"expected": float("nan"), "claim": 1}):
            with self.subTest(case=repr(broken)):
                self.assertEqual(evaluate(broken)["mark"], "спорно")


if __name__ == "__main__":
    unittest.main()
