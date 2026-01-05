--This query adds columns and data that exist in macrostrat and not in macrostrat_temp

--Used this script to add best_interval_id column into macrostrat_temp.lookup_unit_intervals
--https://github.com/UW-Macrostrat/macrostrat/blob/7aefe2d0cc89a738b356ff444b7b3dd0fd85e607/cli/macrostrat/cli/commands/table_meta/lookup_unit_intervals/4-process.sql#L21

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
   AS b_interval_id from macrostrat_temp.lookup_unit_intervals
)
UPDATE macrostrat_temp.lookup_unit_intervals lui
SET best_interval_id = b_interval_id
FROM bests
WHERE lui.unit_id = bests.unit_id;
/*
This query copies the table configuration and all data from macrostrat.macrostrat and inserts it
into the macrostrat.temp schema. This is to preserve the data that exists in macrostrat and NOT in
MariaDB before we run the migration.
*/

DO $$
DECLARE
    table_name text;
    source_schema text := 'macrostrat';
    target_schema text := 'macrostrat_temp';
    tables text[] := ARRAY[
        'strat_name_footprints',
        'grainsize',
        'pbdb_collections',
        'pbdb_collections_strat_names'
    ];
BEGIN
    FOREACH table_name IN ARRAY tables
    LOOP
        EXECUTE format('CREATE TABLE IF NOT EXISTS %I.%I (LIKE %I.%I INCLUDING ALL)', target_schema, table_name, source_schema, table_name);
        EXECUTE format('INSERT INTO %I.%I SELECT * FROM %I.%I', target_schema, table_name, source_schema, table_name);
    END LOOP;
END $$;



--from schlep scripts
UPDATE macrostrat_temp.intervals SET rank = 6 WHERE interval_type = 'age';
UPDATE macrostrat_temp.intervals SET rank = 5 WHERE interval_type = 'epoch';
UPDATE macrostrat_temp.intervals SET rank = 4 WHERE interval_type = 'period';
UPDATE macrostrat_temp.intervals SET rank = 3 WHERE interval_type = 'era';
UPDATE macrostrat_temp.intervals SET rank = 2 WHERE interval_type = 'eon';
UPDATE macrostrat_temp.intervals SET rank = 1 WHERE interval_type = 'supereon';
UPDATE macrostrat_temp.intervals SET rank = 0 WHERE rank IS NULL;