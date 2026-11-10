UPDATE macrostrat.intervals i
SET interval_name = 'Late Cretaceous-Paleogene'
FROM macrostrat.intervals t, macrostrat.intervals b
WHERE i.interval_name = 'Cretaceous-Paleogene'
  AND t.interval_name = 'Paleocene' AND i.age_top = t.age_top
  AND b.interval_name = 'Late Cretaceous' AND i.age_bottom = b.age_bottom;

-- The id sequence lags the table in some databases, so take the next id directly.
-- Color is the RGB midpoint of the two periods, as for the other composites.
INSERT INTO macrostrat.intervals (
  id, age_top, age_bottom, interval_name, interval_type, interval_color, orig_color, rank
)
SELECT
  (SELECT max(id) + 1 FROM macrostrat.intervals),
  t.age_top, b.age_bottom, 'Cretaceous-Paleogene', 'period', '#BEB050', '#BEB050', 4
FROM macrostrat.intervals t, macrostrat.intervals b
WHERE t.interval_name = 'Paleogene' AND b.interval_name = 'Cretaceous'
  AND NOT EXISTS (
    SELECT 1 FROM macrostrat.intervals WHERE interval_name = 'Cretaceous-Paleogene'
  );
