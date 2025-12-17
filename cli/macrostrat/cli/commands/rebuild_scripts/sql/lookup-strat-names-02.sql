/** NOTE: this SQL still runs in MariaDB, not PostgreSQL, and needs to be updated */

-- Populate the fields `parent` and `tree`
UPDATE lookup_strat_names_new
SET parent = CASE
                 WHEN bed_id > 0 AND strat_name_id != bed_id THEN bed_id
                 WHEN mbr_id > 0 AND strat_name_id != mbr_id THEN mbr_id
                 WHEN fm_id > 0 AND strat_name_id != fm_id THEN fm_id
                 WHEN subgp_id > 0 AND strat_name_id != subgp_id THEN subgp_id
                 WHEN gp_id > 0 AND strat_name_id != gp_id THEN gp_id
                 WHEN sgp_id > 0 AND strat_name_id != sgp_id THEN sgp_id
                 ELSE strat_name_id
    END,
    tree = CASE
               WHEN sgp_id > 0 THEN sgp_id
               WHEN gp_id > 0 THEN gp_id
               WHEN subgp_id > 0 THEN subgp_id
               WHEN fm_id > 0 THEN fm_id
               WHEN mbr_id > 0 THEN mbr_id
               WHEN bed_id > 0 THEN bed_id
               ELSE tree = 0
        END;

-- Group by concept_id and fill in NULL ages

UPDATE lookup_strat_names_new lsn
    LEFT JOIN (
    SELECT concept_id, max(b_age) AS early_age, min(t_age) AS late_age
    FROM lookup_strat_names_new
    LEFT JOIN unit_strat_names USING (strat_name_id)
    LEFT JOIN lookup_unit_intervals USING (unit_id)
    WHERE concept_id != 0
    GROUP BY strat_name_id
) AS sub USING (concept_id)
SET lsn.early_age = sub.early_age, lsn.late_age = sub.late_age
 WHERE lsn.early_age IS NULL AND lsn.late_age IS NULL;

-- Group by concept_id, but using strat names meta

UPDATE lookup_strat_names_new lsn
    LEFT JOIN (
    SELECT concept_id, b.age_bottom, t.age_top
    FROM strat_names_meta
    JOIN intervals b on b.id = b_int
    JOIN intervals t ON t.id = t_int
    ) AS sub USING (concept_id)
SET lsn.early_age = sub.age_bottom, lsn.late_age = sub.age_top
WHERE lsn.early_age IS NULL AND lsn.late_age IS NULL;

-- Group by parent and fill in NULL ages
UPDATE lookup_strat_names_new lsn
    LEFT JOIN (
    SELECT parent, max(b_age) AS early_age, min(t_age) AS late_age
    FROM lookup_strat_names_new
    LEFT JOIN unit_strat_names USING (strat_name_id)
    LEFT JOIN lookup_unit_intervals USING (unit_id)
    GROUP BY parent
    ) AS sub USING (parent)
SET lsn.early_age = sub.early_age, lsn.late_age = sub.late_age
 WHERE lsn.early_age IS NULL AND lsn.late_age IS NULL;

-- Group by tree and fill in NULL ages
UPDATE lookup_strat_names_new lsn
    LEFT JOIN (
    SELECT tree, max(b_age) AS early_age, min(t_age) AS late_age
    FROM lookup_strat_names
    LEFT JOIN unit_strat_names USING (strat_name_id)
    LEFT JOIN lookup_unit_intervals USING (unit_id)
    GROUP BY tree
    ) AS sub USING (tree)
SET lsn.early_age = sub.early_age, lsn.late_age = sub.late_age
 WHERE lsn.early_age IS NULL AND lsn.late_age IS NULL;

-- Populate the fields `b_period` and `t_period`

UPDATE lookup_strat_names_new
SET b_period = (
    SELECT interval_name
    FROM macrostrat.intervals
             JOIN timescales_intervals ON intervals.id = timescales_intervals.interval_id
             JOIN timescales ON timescales.id = timescales_intervals.timescale_id
    WHERE age_bottom >= early_age AND age_top <= early_age
      AND timescales.id = 20
    LIMIT 1
);


UPDATE lookup_strat_names_new
SET t_period = (
    SELECT interval_name
    FROM intervals
             JOIN timescales_intervals ON intervals.id = timescales_intervals.interval_id
             JOIN timescales ON timescales.id = timescales_intervals.timescale_id
    WHERE age_bottom >= late_age AND age_top <= late_age
      AND timescales.id = 20
    LIMIT 1
);

-- Update containing interval for names not explicitly matched to units but have a concept_id
UPDATE lookup_strat_names_new
    JOIN strat_names_meta USING (concept_id)
    JOIN intervals t on t.id = t_int
    JOIN intervals b on b.id = b_int
SET c_interval = (
    SELECT interval_name
    FROM intervals
             JOIN timescales_intervals ON intervals.id = interval_id
             JOIN timescales ON timescale_id = timescales.id
    WHERE timescale = 'international'
      AND b.age_bottom > age_top
      AND b.age_bottom <= age_bottom
      AND t.age_top < age_bottom
      AND t.age_top >= age_top
    ORDER BY age_bottom - age_top
    LIMIT 1
),
    b_period = (
    SELECT interval_name
    FROM intervals
    JOIN timescales_intervals ON intervals.id = interval_id
    JOIN timescales ON timescale_id = timescales.id
    WHERE timescale = 'international periods'
        AND b.age_bottom > age_top
        AND b.age_bottom <= age_bottom
        AND b.age_top < age_bottom
        AND b.age_top >= age_top
    ORDER BY age_bottom - age_top
    LIMIT 1
),
t_period = (
    SELECT interval_name
    FROM intervals
    JOIN timescales_intervals ON intervals.id = interval_id
    JOIN timescales ON timescale_id = timescales.id
    WHERE timescale = 'international periods'
        AND t.age_bottom > age_top
        AND t.age_bottom <= age_bottom
        AND t.age_top < age_bottom
        AND t.age_top >= age_top
    ORDER BY age_bottom - age_top
    LIMIT 1
)
WHERE c_interval IS NULL and t_int > 0 and b_int > 0;
