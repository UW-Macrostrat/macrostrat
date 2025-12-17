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


-- Out with the old, in with the new
TRUNCATE lookup_strat_names;
INSERT INTO lookup_strat_names SELECT * FROM lookup_strat_names_new;
DROP TABLE lookup_strat_names_new;
