-- First read-only queries on the station database.
-- Every query starts with a comment saying what ONE row of the result means.

-- 1. Одна строка = один завершённый опыт + его руководитель.
SELECT
    e.experiment_id,
    e.title,
    e.finished_at,
    p.person_id AS leader_id,
    p.name AS leader_name
FROM experiments AS e
JOIN people AS p ON p.person_id = e.leader_id
WHERE e.status = 'completed'
ORDER BY e.experiment_id;

-- 2a. Одна строка = один участник опыта 101.
SELECT
    p.person_id,
    p.name,
    p.specialty,
    pa.role
FROM participation AS pa
JOIN people AS p ON p.person_id = pa.person_id
WHERE pa.experiment_id = 101
ORDER BY p.person_id;

-- 2b. Одна строка = одно измерение опыта 101.
SELECT
    measurement_id,
    metric,
    value,
    unit,
    measured_at,
    quality
FROM measurements
WHERE experiment_id = 101
ORDER BY measurement_id;

-- 3. Одна строка = один прибор, у которого вообще нет записи об осмотре.
SELECT
    e.equipment_id,
    e.name,
    e.serial
FROM equipment AS e
LEFT JOIN inspections AS i ON i.equipment_id = e.equipment_id
WHERE i.inspection_id IS NULL
ORDER BY e.equipment_id;
