"""Правило проверки одного числового утверждения модели.

Что делает правило: сравнивает число claim (его из ответа модели достал человек)
с числом expected (его независимо получил SQL на учебной базе).

Единицы: claim и expected обязаны быть в одних единицах (например, оба в граммах).
Правило единицы не переводит: перевод и извлечение числа делает человек.

Точность: по умолчанию допустимая разница |claim - expected| <= 1e-9. Для целых
(счётчиков) это значит точное совпадение. Если ответ округлён, человек заранее
пишет в случае поле tolerance (например, 0.05 для среднего с двумя знаками).

Чего правило не видит: рассуждение, SQL и смысл ответа, неоднозначность вопроса,
неверную предпосылку. Правильное число из неверного рассуждения оно пропустит.
"""
import math

PASS = "прошёл"
FAIL = "не прошёл"
UNCLEAR = "спорно"

DEFAULT_TOLERANCE = 1e-9


def _is_number(value):
    """Конечное число? bool, строка, None, NaN и бесконечность числом не считаем."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return math.isfinite(value)


def _result(mark, reason):
    return {"mark": mark, "reason": reason}


def evaluate(case):
    """Принимает словарь случая, возвращает {'mark': ..., 'reason': ...}."""
    if not isinstance(case, dict):
        return _result(UNCLEAR, "Случай не словарь: проверять нечего (проблема проверки, не модели).")

    expected = case.get("expected")
    if not _is_number(expected):
        return _result(UNCLEAR, "expected не конечное число: эталон испорчен, это проблема проверки, не ошибка модели.")

    claim = case.get("claim")
    if claim is None:
        return _result(UNCLEAR, "Числового утверждения нет или его нельзя однозначно извлечь: не доказывает ошибку модели.")
    if not _is_number(claim):
        return _result(UNCLEAR, "claim не является конечным числом (bool, строка, NaN или бесконечность): однозначного утверждения нет.")

    tolerance = case.get("tolerance", DEFAULT_TOLERANCE)
    if not _is_number(tolerance) or tolerance < 0:
        return _result(UNCLEAR, "tolerance должна быть конечным числом не меньше нуля: правило применить нельзя.")

    difference = abs(claim - expected)
    if difference <= tolerance:
        return _result(PASS, "claim=%s совпадает с expected=%s (разница %s, допуск %s)." % (claim, expected, difference, tolerance))
    return _result(FAIL, "claim=%s не совпадает с expected=%s (разница %s больше допуска %s)." % (claim, expected, difference, tolerance))
