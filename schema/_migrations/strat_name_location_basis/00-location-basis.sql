CREATE TYPE maps.strat_name_location_basis AS ENUM (
    'column_unit',
    'adjacent_column',
    'footprint',
    'none'
);

/* The view reads the column being replaced, so it goes first and comes back at
   the end against the new one. */
DROP VIEW IF EXISTS maps.map_strat_names;

ALTER TABLE maps.legend_strat_names
    ADD COLUMN location_basis maps.strat_name_location_basis;

/* The boolean said only whether a footprint was reached. FALSE meant the match
   was admitted on a buffered footprint and nothing stronger, which is the new
   scale's weakest rung; TRUE meant a footprint was met. Neither can express the
   column rungs, so no existing row can claim one -- a re-match assigns those. */
UPDATE maps.legend_strat_names
SET location_basis = CAST(
        CASE WHEN in_footprint THEN 'footprint' ELSE 'none' END
        AS maps.strat_name_location_basis
    )
WHERE in_footprint IS NOT NULL;

ALTER TABLE maps.legend_strat_names DROP COLUMN in_footprint;

CREATE VIEW maps.map_strat_names AS
SELECT
    ml.map_id,
    lsn.strat_name_id,
    (CASE
        WHEN lsn.is_manual THEN 'manual'
        ELSE lsn.match_field::text
            || CASE WHEN lsn.location_basis = 'none' THEN '_fspace' ELSE '' END
            || CASE
                   WHEN lsn.age_overlaps IS NULL THEN '_ntime'
                   WHEN lsn.age_overlaps IS FALSE THEN '_ftime'
                   ELSE ''
               END
    END)::character varying(50) AS basis_col
FROM maps.legend_strat_names lsn
JOIN maps.map_legend ml ON ml.legend_id = lsn.legend_id;
