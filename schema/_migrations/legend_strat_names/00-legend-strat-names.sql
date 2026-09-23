/* Move stratigraphic-name matches onto legend grain, and leave
   `maps.map_strat_names` as a view under its old name.
   Rationale: `Feature areas/Data management/Map geologic name matching`. */

/* Clear a run that failed partway. `map_strat_names` still being a table means
   the switchover did not complete, so anything under these names is debris. */
DO $$
BEGIN
  IF (SELECT c.relkind FROM pg_class c
      JOIN pg_namespace n ON n.oid = c.relnamespace
      WHERE n.nspname = 'maps' AND c.relname = 'map_strat_names') = 'r'
  THEN
    DROP TABLE IF EXISTS maps.map_strat_names_backup;
    DROP TABLE IF EXISTS maps.legend_strat_names;
    DROP TYPE IF EXISTS maps.strat_name_match_field;
    DROP TYPE IF EXISTS maps.strat_name_location_basis;
  END IF;
END
$$;

CREATE TYPE maps.strat_name_match_field AS ENUM (
    'strat_name',
    'name',
    'descrip',
    'comments'
);

CREATE TYPE maps.strat_name_location_basis AS ENUM (
    'column_unit',
    'adjacent_column',
    'footprint',
    'none'
);

CREATE TABLE maps.legend_strat_names (
    legend_id integer NOT NULL
        REFERENCES maps.legend (legend_id) ON DELETE CASCADE,
    strat_name_id integer NOT NULL,
    match_field maps.strat_name_match_field NOT NULL,
    rank_agrees boolean,
    location_basis maps.strat_name_location_basis,
    age_overlaps boolean,
    is_manual boolean NOT NULL DEFAULT false,
    matched_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (legend_id, strat_name_id, match_field)
);

CREATE INDEX legend_strat_names_strat_name_id_idx
    ON maps.legend_strat_names USING btree (strat_name_id);

CREATE INDEX legend_strat_names_manual_idx
    ON maps.legend_strat_names USING btree (legend_id) WHERE is_manual;

/* Kept, not dropped: the old rows are the only record of what was served
   before, and the only thing to diff a re-match against. */
ALTER TABLE maps.map_strat_names RENAME TO map_strat_names_backup;

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

/* Only the manual matches carry over -- 152 of them. The rest is matcher output,
   reproduced by re-running a matcher, and its `basis_col` values describe a
   comparison this schema no longer makes. `DISTINCT` returns a judgment made once
   per legend entry to that grain; the backup holds it once per polygon. */
INSERT INTO maps.legend_strat_names
  (legend_id, strat_name_id, match_field, is_manual, matched_at)
SELECT DISTINCT
  ml.legend_id,
  msn.strat_name_id,
  'strat_name'::maps.strat_name_match_field,
  true,
  '-infinity'::timestamptz
FROM maps.map_strat_names_backup msn
JOIN maps.map_legend ml ON ml.map_id = msn.map_id
JOIN maps.legend l ON l.legend_id = ml.legend_id
WHERE msn.basis_col LIKE 'manual%'
ON CONFLICT DO NOTHING;
