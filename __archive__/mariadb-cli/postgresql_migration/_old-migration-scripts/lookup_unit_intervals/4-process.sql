
WITH bests AS (
  select unit_id,
    CASE
      WHEN age_id > 0 THEN
        age_id
      WHEN epoch_id > 0 THEN
        epoch_id
      WHEN period_id > 0 THEN
        period_id
      WHEN era_id > 0 THEN
        era_id
      WHEN eon_id > 0 THEN
        eon_id
      ELSE
        0
    END
   AS b_interval_id from macrostrat.lookup_unit_intervals_new
)
UPDATE macrostrat.lookup_unit_intervals_new lui
SET best_interval_id = b_interval_id
FROM bests
WHERE lui.unit_id = bests.unit_id;

