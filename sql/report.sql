-- ЗАДАНИЕ 6. Запросы отчёта по журналу eval_journal.db (только чтение).
-- Файл делится на блоки строками вида "-- name: имя". report.py находит блок по имени.
-- Блоки с именем u_... используют общую часть units: Python подставляет её как WITH units AS (...).
--
-- ЕДИНИЦА СЧЁТА (units): одна строка = одна оценка основной стороны качества.
--   * одиночный ответ (ref вида a12): этап main, формулировка не shortened, оценка по cases.dimension_id;
--   * пара ответов (ref вида p3): обе попытки main и не shortened, оценка stability.
-- Соединение с assessments идёт по ключу (attempt_id, dimension_id) и он уникален,
-- поэтому ответ не размножается: на ответ приходится не больше одной строки.

-- name: units
SELECT 'a' || a.attempt_id AS ref,
       c.case_id,
       c.kind,
       c.dimension_id,
       s.verdict
FROM attempts AS a
JOIN prompts AS p ON p.prompt_id = a.prompt_id
JOIN cases AS c ON c.case_id = p.case_id
JOIN assessments AS s ON s.attempt_id = a.attempt_id AND s.dimension_id = c.dimension_id
WHERE a.phase = 'main' AND p.label <> 'shortened'
UNION ALL
SELECT 'p' || pr.pair_id,
       c.case_id,
       c.kind,
       'stability',
       s.verdict
FROM pairs AS pr
JOIN attempts AS l ON l.attempt_id = pr.left_attempt_id
JOIN attempts AS r ON r.attempt_id = pr.right_attempt_id
JOIN prompts AS pl ON pl.prompt_id = l.prompt_id
JOIN prompts AS prr ON prr.prompt_id = r.prompt_id
JOIN cases AS c ON c.case_id = pl.case_id
JOIN assessments AS s ON s.pair_id = pr.pair_id
WHERE l.phase = 'main' AND r.phase = 'main'
  AND pl.label <> 'shortened' AND prr.label <> 'shortened';

-- name: totals
-- Пункт 1. Одна строка = общие числа журнала: разные случаи, формулировки, пары (с номерами).
SELECT (SELECT COUNT(*) FROM cases) AS cases_n,
       (SELECT group_concat(case_id, ',') FROM (SELECT case_id FROM cases ORDER BY case_id)) AS cases_ids,
       (SELECT COUNT(*) FROM prompts) AS prompts_n,
       (SELECT group_concat(prompt_id, ',') FROM (SELECT prompt_id FROM prompts ORDER BY prompt_id)) AS prompts_ids,
       (SELECT COUNT(*) FROM pairs) AS pairs_n,
       (SELECT group_concat(pair_id, ',') FROM (SELECT pair_id FROM pairs ORDER BY pair_id)) AS pairs_ids;

-- name: attempts_by_phase
-- Пункт 1. Одна строка = один этап (main, peer, defense): число ответов и их номера.
SELECT phase,
       COUNT(*) AS n,
       group_concat(attempt_id, ',') AS ids
FROM (SELECT phase, attempt_id FROM attempts ORDER BY attempt_id)
GROUP BY phase
ORDER BY phase;

-- name: u_by_dimension
-- Пункты 2 и 3. Одна строка = одна сторона качества (все пять, даже без оценок).
-- LEFT JOIN сохраняет сторону без оценок, тогда все счётчики равны 0.
-- fail_rate = fail / (pass + fail). NULLIF превращает нулевой знаменатель в NULL, а не в ошибку.
SELECT d.dimension_id,
       d.title,
       SUM(CASE WHEN u.verdict = 'pass'    THEN 1 ELSE 0 END) AS passed,
       SUM(CASE WHEN u.verdict = 'fail'    THEN 1 ELSE 0 END) AS failed,
       SUM(CASE WHEN u.verdict = 'unclear' THEN 1 ELSE 0 END) AS unclear,
       SUM(CASE WHEN u.verdict = 'na'      THEN 1 ELSE 0 END) AS na,
       CAST(SUM(CASE WHEN u.verdict = 'fail' THEN 1 ELSE 0 END) AS REAL)
         / NULLIF(SUM(CASE WHEN u.verdict IN ('pass', 'fail') THEN 1 ELSE 0 END), 0) AS fail_rate,
       group_concat(CASE WHEN u.verdict = 'pass'    THEN u.ref END, ',') AS pass_refs,
       group_concat(CASE WHEN u.verdict = 'fail'    THEN u.ref END, ',') AS fail_refs,
       group_concat(CASE WHEN u.verdict = 'unclear' THEN u.ref END, ',') AS unclear_refs,
       group_concat(CASE WHEN u.verdict = 'na'      THEN u.ref END, ',') AS na_refs
FROM dimensions AS d
LEFT JOIN units AS u ON u.dimension_id = d.dimension_id
GROUP BY d.dimension_id
ORDER BY d.rowid;

-- name: u_by_kind
-- Пункт 4. Одна строка = один вид случая: normal, challenge (одиночные ответы) или pair (пары stability).
-- Для pair total это число оценённых пар. Знаменатели видов и пар не складываются.
SELECT u.kind,
       COUNT(*) AS total,
       SUM(CASE WHEN u.verdict = 'pass'    THEN 1 ELSE 0 END) AS passed,
       SUM(CASE WHEN u.verdict = 'fail'    THEN 1 ELSE 0 END) AS failed,
       SUM(CASE WHEN u.verdict = 'unclear' THEN 1 ELSE 0 END) AS unclear,
       SUM(CASE WHEN u.verdict = 'na'      THEN 1 ELSE 0 END) AS na,
       CAST(SUM(CASE WHEN u.verdict = 'fail' THEN 1 ELSE 0 END) AS REAL)
         / NULLIF(SUM(CASE WHEN u.verdict IN ('pass', 'fail') THEN 1 ELSE 0 END), 0) AS fail_rate,
       group_concat(u.ref, ',') AS refs
FROM units AS u
GROUP BY u.kind;

-- name: repeats
-- Пункт 5. Одна строка = одна исходная формулировка, на которую есть 3 и больше ответов main
-- (повторённый вопрос задания 5). Считаем ответы и оценки по основной стороне качества случая.
-- LEFT JOIN не теряет ответ без оценки (not_assessed), а ключ (attempt_id, dimension_id) уникален.
SELECT p.prompt_id,
       p.case_id,
       c.dimension_id,
       COUNT(a.attempt_id) AS answers,
       SUM(CASE WHEN s.verdict = 'fail'              THEN 1 ELSE 0 END) AS failed,
       SUM(CASE WHEN s.verdict = 'pass'              THEN 1 ELSE 0 END) AS passed,
       SUM(CASE WHEN s.verdict IN ('unclear', 'na')  THEN 1 ELSE 0 END) AS other,
       SUM(CASE WHEN s.verdict IS NULL               THEN 1 ELSE 0 END) AS not_assessed,
       group_concat(a.attempt_id, ',') AS attempt_ids,
       group_concat(CASE WHEN s.verdict = 'fail' THEN a.attempt_id END, ',') AS fail_ids
FROM prompts AS p
JOIN cases AS c ON c.case_id = p.case_id
JOIN attempts AS a ON a.prompt_id = p.prompt_id AND a.phase = 'main'
LEFT JOIN assessments AS s ON s.attempt_id = a.attempt_id AND s.dimension_id = c.dimension_id
WHERE p.label = 'original' AND c.dimension_id <> 'stability'
GROUP BY p.prompt_id
HAVING COUNT(a.attempt_id) >= 3
ORDER BY p.prompt_id;

-- name: shortened
-- Пункт 5. Одна строка = одна сокращённая формулировка (label = shortened). Считается отдельно от повторов.
SELECT p.prompt_id,
       p.case_id,
       c.dimension_id,
       COUNT(a.attempt_id) AS answers,
       SUM(CASE WHEN s.verdict = 'fail'              THEN 1 ELSE 0 END) AS failed,
       SUM(CASE WHEN s.verdict = 'pass'              THEN 1 ELSE 0 END) AS passed,
       SUM(CASE WHEN s.verdict IN ('unclear', 'na')  THEN 1 ELSE 0 END) AS other,
       SUM(CASE WHEN s.verdict IS NULL               THEN 1 ELSE 0 END) AS not_assessed,
       group_concat(a.attempt_id, ',') AS attempt_ids,
       group_concat(CASE WHEN s.verdict = 'fail' THEN a.attempt_id END, ',') AS fail_ids
FROM prompts AS p
JOIN cases AS c ON c.case_id = p.case_id
JOIN attempts AS a ON a.prompt_id = p.prompt_id AND a.phase = 'main'
LEFT JOIN assessments AS s ON s.attempt_id = a.attempt_id AND s.dimension_id = c.dimension_id
WHERE p.label = 'shortened'
GROUP BY p.prompt_id
ORDER BY p.prompt_id;

-- name: extra_phases
-- Отдельно от основного отчёта. Одна строка = один этап (peer или defense): ответы и их основные оценки.
-- Ответы случаев stability не имеют одиночной оценки, они попадают в without_single_mark.
SELECT a.phase,
       COUNT(a.attempt_id) AS answers,
       SUM(CASE WHEN s.verdict = 'pass'    THEN 1 ELSE 0 END) AS passed,
       SUM(CASE WHEN s.verdict = 'fail'    THEN 1 ELSE 0 END) AS failed,
       SUM(CASE WHEN s.verdict = 'unclear' THEN 1 ELSE 0 END) AS unclear,
       SUM(CASE WHEN s.verdict = 'na'      THEN 1 ELSE 0 END) AS na,
       SUM(CASE WHEN s.verdict IS NULL     THEN 1 ELSE 0 END) AS without_single_mark,
       group_concat(a.attempt_id, ',') AS attempt_ids
FROM attempts AS a
JOIN prompts AS p ON p.prompt_id = a.prompt_id
JOIN cases AS c ON c.case_id = p.case_id
LEFT JOIN assessments AS s ON s.attempt_id = a.attempt_id AND s.dimension_id = c.dimension_id
WHERE a.phase IN ('peer', 'defense')
GROUP BY a.phase
ORDER BY a.phase;

-- name: secondary
-- Дополнительные оценки ответов main (не по основной стороне случая), показываются отдельно.
-- Одна строка = одна сторона качества, по которой ставились дополнительные оценки.
SELECT s.dimension_id,
       COUNT(*) AS total,
       SUM(CASE WHEN s.verdict = 'pass'    THEN 1 ELSE 0 END) AS passed,
       SUM(CASE WHEN s.verdict = 'fail'    THEN 1 ELSE 0 END) AS failed,
       SUM(CASE WHEN s.verdict = 'unclear' THEN 1 ELSE 0 END) AS unclear,
       SUM(CASE WHEN s.verdict = 'na'      THEN 1 ELSE 0 END) AS na,
       group_concat('a' || s.attempt_id, ',') AS refs
FROM assessments AS s
JOIN attempts AS a ON a.attempt_id = s.attempt_id
JOIN prompts AS p ON p.prompt_id = a.prompt_id
JOIN cases AS c ON c.case_id = p.case_id
WHERE a.phase = 'main' AND s.dimension_id <> c.dimension_id
GROUP BY s.dimension_id
ORDER BY s.dimension_id;

-- name: unassessed
-- Что осталось без оценки и потому в итоги не вошло (пустое место не считается успехом).
-- Одна строка = одна запись без оценки: ответ, ответ stability вне пары или пара без оценки.
SELECT 'ответ без основной оценки' AS what, 'a' || a.attempt_id AS ref
FROM attempts AS a
JOIN prompts AS p ON p.prompt_id = a.prompt_id
JOIN cases AS c ON c.case_id = p.case_id
LEFT JOIN assessments AS s ON s.attempt_id = a.attempt_id AND s.dimension_id = c.dimension_id
WHERE a.phase = 'main' AND c.dimension_id <> 'stability' AND s.assessment_id IS NULL
UNION ALL
SELECT 'ответ stability не вошёл ни в одну пару', 'a' || a.attempt_id
FROM attempts AS a
JOIN prompts AS p ON p.prompt_id = a.prompt_id
JOIN cases AS c ON c.case_id = p.case_id
WHERE a.phase = 'main' AND c.dimension_id = 'stability'
  AND a.attempt_id NOT IN (SELECT left_attempt_id FROM pairs UNION SELECT right_attempt_id FROM pairs)
UNION ALL
SELECT 'пара без оценки', 'p' || pr.pair_id
FROM pairs AS pr
LEFT JOIN assessments AS s ON s.pair_id = pr.pair_id
WHERE s.assessment_id IS NULL;

-- name: exclusions
-- Заметки о технических исключениях: сбои сервиса, исправленные записи ввода. Одна строка = одна заметка.
SELECT note_id, topic, substr(text, 1, 300) AS text_start
FROM notes
WHERE topic LIKE 'Исключ%' OR topic LIKE 'Исправл%' OR topic LIKE 'Сбой%'
ORDER BY note_id;
