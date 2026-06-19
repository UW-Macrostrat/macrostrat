-- Make sure all names have an early and late_age

SET SEARCH_PATH to macrostrat, public;

UPDATE lookup_strat_names_new
SET early_age = (
    SELECT age_bottom
    FROM macrostrat.intervals
    WHERE interval_name = b_period
    LIMIT 1
), late_age = (
    SELECT age_top
    FROM macrostrat.intervals
    WHERE interval_name = t_period
    LIMIT 1
) WHERE early_age IS NULL AND late_age IS NULL;

-- Populate containing interval

UPDATE macrostrat.lookup_strat_names_new
SET c_interval = (
  SELECT interval_name from intervals
    JOIN timescales_intervals ON intervals.id = interval_id
    JOIN timescales on timescale_id = timescales.id
  WHERE timescale = 'international'
    AND early_age > age_top
    AND early_age <= age_bottom
    AND late_age < age_bottom
    AND late_age >= age_top
  ORDER BY age_bottom - age_top
  LIMIT 1
);
-- Normalize missing lookup IDs/counts to 0 for legacy v2 API/Sift compatibility.
-- The v2 /defs/strat_names endpoint returns these fields directly from
-- macrostrat.lookup_strat_names, so nulls here can break legacy hierarchy rendering
UPDATE macrostrat.lookup_strat_names_new
SET
    concept_id = COALESCE(concept_id, 0),
    bed_id = COALESCE(bed_id, 0),
    mbr_id = COALESCE(mbr_id, 0),
    fm_id = COALESCE(fm_id, 0),
    subgp_id = COALESCE(subgp_id, 0),
    gp_id = COALESCE(gp_id, 0),
    t_units = COALESCE(t_units, 0)
WHERE
    concept_id IS NULL OR
    bed_id IS NULL OR
    mbr_id IS NULL OR
    fm_id IS NULL OR
    subgp_id IS NULL OR
    gp_id IS NULL OR
    t_units IS NULL;

ALTER TABLE macrostrat.lookup_strat_names
  RENAME TO lookup_strat_names_old;
ALTER TABLE macrostrat.lookup_strat_names_new
  RENAME TO lookup_strat_names;
DROP TABLE IF EXISTS macrostrat.lookup_strat_names_old;

