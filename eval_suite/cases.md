# Набор тестовых случаев (eval suite)

Десять случаев по пяти сторонам качества. У каждого: формулировка вопроса к модели, ожидаемое поведение, **независимый SQL-эталон** и пояснение, почему эталон однозначен. Эталоны выполняются командой `python3 src/verify_cases.py`.

## Случай 1. Руководитель опыта 103

- Сторона качества: **Понимание данных** (`meaning`), тип: `normal`
- Формулировка (original): Кто руководил опытом 103? Назови имя, специальность и person_id.

**Ожидаемое поведение.** Модель называет руководителя из experiments.leader_id: person_id 4, Алина Орлова, инженер. Не путает её с Алиной Орловой, биологом (person 1), и не берёт имя из participation.

**Эталонный SQL.**

```sql
SELECT e.experiment_id, e.leader_id, p.name, p.specialty FROM experiments AS e JOIN people AS p ON p.person_id = e.leader_id WHERE e.experiment_id = 103;
```

**Что показывает эталон.** Результат: одна строка (103, 4, Алина Орлова, инженер). Руководитель однозначно определён по leader_id = 4. Трудность обычная: рядом есть тёзка (person 1), поэтому в вопросе просим person_id.

## Случай 2. Ложная предпосылка: руководитель 105 среди участников

- Сторона качества: **Понимание данных** (`meaning`), тип: `challenge`
- Формулировка (original): Руководитель опыта 105 тоже входил в список участников этого опыта. Подскажи, как его зовут и какая роль у него записана в опыте 105?

**Ожидаемое поведение.** Модель замечает, что предпосылка ложна: руководитель опыта 105 (person 1, Алина Орлова, биолог) не входит в participation этого опыта, там только person 5 (Денис Волков, техник). Роли у руководителя в опыте 105 в базе нет. Модель не выдумывает роль (например, наблюдатель из других опытов).

**Эталонный SQL.**

```sql
SELECT e.experiment_id, e.status, e.leader_id, p.name, p.specialty FROM experiments AS e JOIN people AS p ON p.person_id = e.leader_id WHERE e.experiment_id = 105;
SELECT pa.person_id, p.name, pa.role FROM participation AS pa JOIN people AS p ON p.person_id = pa.person_id WHERE pa.experiment_id = 105;
SELECT COUNT(*) AS leader_in_participation FROM participation AS pa JOIN experiments AS e ON e.experiment_id = pa.experiment_id WHERE e.experiment_id = 105 AND pa.person_id = e.leader_id;
```

**Что показывает эталон.** Результаты: 105, cancelled, leader_id 1, Алина Орлова, биолог; participation для 105: одна строка (person 5, Денис Волков, техник); руководитель среди участников: 0 строк. Предпосылка опровергнута строками базы. Трудность: ложное предположение в вопросе.

## Случай 3. Число достоверных измерений

- Сторона качества: **Правильность расчёта** (`calculation`), тип: `normal`
- Формулировка (original): Сколько записей в таблице measurements имеют quality = 'valid'?

**Ожидаемое поведение.** Ответ 11: записи с quality = valid.

**Эталонный SQL.**

```sql
SELECT COUNT(*) FROM measurements WHERE quality = 'valid';
SELECT measurement_id FROM measurements WHERE quality = 'valid' ORDER BY measurement_id;
```

**Что показывает эталон.** Результат: 11 записей: 1001, 1002, 1004, 1006, 1007, 1008, 1009, 1010, 1011, 1012, 1014. Не входят: 1003 и 1013 (missing), 1005 (suspect). Обычный случай: условие названо явно, JOIN не нужен.

## Случай 4. Измерения в июле 2026 (граница месяца)

- Сторона качества: **Правильность расчёта** (`calculation`), тип: `challenge`
- Формулировка (original): Посмотри на таблицу measurements и скажи, пожалуйста, сколько всего записей измерений имеют время measured_at, которое приходится на июль 2026 года по UTC?

**Ожидаемое поведение.** Ответ 10. Месяц это интервал от 2026-07-01 00:00:00 включительно до 2026-08-01 00:00:00 не включительно. Запись 1010 (2026-08-01 00:00:00) в июль не входит; записи 1001, 1002, 1003 (июнь) тоже.

**Эталонный SQL.**

```sql
SELECT COUNT(*) FROM measurements WHERE measured_at >= '2026-07-01 00:00:00' AND measured_at < '2026-08-01 00:00:00';
SELECT measurement_id, measured_at FROM measurements WHERE measured_at < '2026-07-01 00:00:00' OR measured_at >= '2026-08-01 00:00:00' ORDER BY measurement_id;
SELECT COUNT(*) AS wrong_if_lte FROM measurements WHERE measured_at >= '2026-07-01 00:00:00' AND measured_at <= '2026-08-01 00:00:00';
```

**Что показывает эталон.** Результаты: июль = 10 записей; вне июля 4 записи (1001, 1002, 1003 в июне, 1010 ровно 1 августа 00:00:00). Если включить границу (<=), получится 11: типичная ошибка. Всего записей 14, 14 - 4 = 10. Трудность: граница периода.

## Случай 5. pH в опыте 107 (данные есть)

- Сторона качества: **Работа с неизвестным** (`missing`), тип: `normal`
- Формулировка (original): Какое значение pH измерено в опыте 107?

**Ожидаемое поведение.** Модель отвечает, что pH равен 7: две записи 1011 и 1012 (10:00 и 11:00), обе valid и обе 7. Без лишнего отказа. Хорошо, если отмечено, что записи две.

**Эталонный SQL.**

```sql
SELECT measurement_id, metric, value, unit, measured_at, quality FROM measurements WHERE experiment_id = 107;
```

**Что показывает эталон.** Результат: 1011 (7.0 pH, 2026-07-08 10:00:00, valid) и 1012 (7.0 pH, 2026-07-08 11:00:00, valid). Отчёт 305 подтверждает, что это два разных измерения. Данные есть, отказ был бы ошибкой.

## Случай 6. Напряжение в опыте 108 (значение NULL)

- Сторона качества: **Работа с неизвестным** (`missing`), тип: `challenge`
- Формулировка (original): Подскажи, пожалуйста, сколько вольт показало измерение напряжения, которое сделали в опыте 108?

**Ожидаемое поведение.** Модель говорит, что значение напряжения неизвестно: запись 1013 есть, но value = NULL и quality = missing (число не получено). Не отвечает 0 V и не придумывает число. Называет, чего не хватает: полученного значения.

**Эталонный SQL.**

```sql
SELECT measurement_id, metric, value, unit, quality FROM measurements WHERE experiment_id = 108;
SELECT report_id, version, conclusion FROM reports WHERE experiment_id = 108;
```

**Что показывает эталон.** Результаты: единственная запись 1013 (voltage, NULL, V, missing). Отчёт 306: значение напряжения не получено. Правильный ответ: неизвестно, не ноль. Трудность: пропуск (NULL).

## Случай 7. Самый длинный завершённый опыт (всё задано)

- Сторона качества: **Работа с неоднозначностью** (`ambiguity`), тип: `normal`
- Формулировка (original): Какой из завершённых опытов длился дольше всех, если считать длительность от started_at до finished_at? Назови experiment_id.

**Ожидаемое поведение.** Ответ: опыт 101 (40 часов от 2026-06-29 08:00:00 до 2026-07-01 00:00:00). Все условия заданы в вопросе, поэтому уточнения не нужны: модель отвечает сразу. Опыт 104 почти равен (39 ч 59 мин 59 с), но короче.

**Эталонный SQL.**

```sql
SELECT experiment_id, started_at, finished_at, ROUND((julianday(finished_at) - julianday(started_at)) * 24, 4) AS hours FROM experiments WHERE status = 'completed' ORDER BY hours DESC;
```

**Что показывает эталон.** Результат: 101 = 40.0 ч, 104 = 39.9997 ч, 102 = 28 ч, 107 = 9 ч, 106 и 109 = 2 ч, 108 = 1 ч. Единственный максимум это 101. Вопрос однозначен: завершённые, длительность от started_at до finished_at.

## Случай 8. Опыты Алины Орловой (тёзки)

- Сторона качества: **Работа с неоднозначностью** (`ambiguity`), тип: `challenge`
- Формулировка (original): Скажи, пожалуйста, сколько всего опытов у Алины Орловой?

**Ожидаемое поведение.** Модель замечает неоднозначность и уточняет или делит варианты. Толкование 1: person 1 (биолог): руководила 3 опытами (101, 105, 109), участвовала в 3 (101, 102, 109). Толкование 2: person 4 (инженер): руководила 2 (103, 108), участвовала в 2 (103, 108). Если считать по имени обеих: 5 разных опытов. Молчаливый единый ответ (например, 3) это ошибка.

**Эталонный SQL.**

```sql
SELECT person_id, name, specialty FROM people WHERE name = 'Алина Орлова';
SELECT p.person_id, COUNT(*) AS led_n, GROUP_CONCAT(e.experiment_id) AS led_ids FROM people AS p JOIN experiments AS e ON e.leader_id = p.person_id WHERE p.name = 'Алина Орлова' GROUP BY p.person_id;
SELECT p.person_id, COUNT(*) AS part_n, GROUP_CONCAT(pa.experiment_id) AS part_ids FROM people AS p JOIN participation AS pa ON pa.person_id = p.person_id WHERE p.name = 'Алина Орлова' GROUP BY p.person_id;
```

**Что показывает эталон.** Результаты: двое тёзок: person 1 (биолог) и person 4 (инженер). Руководила: person 1 -> 101, 105, 109; person 4 -> 103, 108. Участвовала: person 1 -> 101, 102, 109; person 4 -> 103, 108. Два разумных толкования («кого имеем в виду» и «руководила или участвовала») дают разные наборы опытов. Трудность: похожие имена.

## Случай 9. Суммарная масса опыта 104 (единицы kg и g)

- Сторона качества: **Устойчивость к перефразированию** (`stability`), тип: `pair`
- Формулировка (original): Какова суммарная масса в граммах по всем измерениям массы в опыте 104?
- Формулировка (paraphrase): Сколько граммов получится, если сложить все измерения массы, сделанные в опыте 104?

**Ожидаемое поведение.** Обе формулировки дают 2000 г: 1.2 kg = 1200 g плюс 800 g. Пара устойчива, если оба ответа по смыслу равны 2000 г. Ошибка при сложении 1.2 + 800 без перевода.

**Эталонный SQL.**

```sql
SELECT measurement_id, value, unit FROM measurements WHERE experiment_id = 104 AND metric = 'mass' ORDER BY measurement_id;
SELECT SUM(CASE unit WHEN 'kg' THEN value * 1000 WHEN 'g' THEN value END) AS total_g FROM measurements WHERE experiment_id = 104 AND metric = 'mass';
```

**Что показывает эталон.** Результаты: 1008 = 1.2 kg, 1009 = 800 g; сумма 2000 г. Формулировки A и B описывают одну задачу: сложить все измерения массы опыта 104 в граммах. Трудность: разные единицы.

## Случай 10. Опыты и с участниками, и с измерениями (размножение строк JOIN)

- Сторона качества: **Устойчивость к перефразированию** (`stability`), тип: `pair`
- Формулировка (original): Сколько разных завершённых опытов имеют и записи об участниках, и записи об измерениях?
- Формулировка (paraphrase): Для скольких различных опытов со статусом completed в базе есть хотя бы один участник и хотя бы одно измерение?

**Ожидаемое поведение.** Обе формулировки дают 7 разных завершённых опытов. Ошибка: 31, если считать строки соединения опытов, участников и измерений (COUNT(*) без DISTINCT).

**Эталонный SQL.**

```sql
SELECT COUNT(DISTINCT e.experiment_id) AS right_answer FROM experiments AS e JOIN participation AS pa ON pa.experiment_id = e.experiment_id JOIN measurements AS m ON m.experiment_id = e.experiment_id WHERE e.status = 'completed';
SELECT COUNT(*) AS wrong_rows FROM experiments AS e JOIN participation AS pa ON pa.experiment_id = e.experiment_id JOIN measurements AS m ON m.experiment_id = e.experiment_id WHERE e.status = 'completed';
```

**Что показывает эталон.** Результаты: 7 разных опытов (101, 102, 104, 106, 107, 108, 109) и 31 строка соединения (101: 3x3, 102: 2x3, 104: 3x2, 106: 2x1, 107: 2x2, 108: 2x1, 109: 2x1 = 9+6+6+2+4+2+2). Формулировки A и B описывают одну задачу. Трудность: повторяющиеся строки.
