SET search_path TO macrostrat, public;

DO $$
DECLARE
  new_count       bigint;
  old_count       bigint;
  empty_geom      bigint;
  invalid_geom    bigint;
  null_geom       bigint;
BEGIN
  --New table must exist and have rows
  SELECT COUNT(*) INTO new_count FROM macrostrat.strat_name_footprints_new;
  IF new_count = 0 THEN
    RAISE EXCEPTION 'Sanity check failed: strat_name_footprints_new is empty';
  END IF;

  --Row count shouldn't drop by more than 10% vs current table
  SELECT COUNT(*) INTO old_count FROM macrostrat.strat_name_footprints;
  IF old_count > 0 AND new_count < old_count * 0.9 THEN
    RAISE EXCEPTION 'Sanity check failed: new table has % rows, old has % (>10%% drop)',
      new_count, old_count;
  END IF;

  --No NULL geometries
  SELECT COUNT(*) INTO null_geom
  FROM macrostrat.strat_name_footprints_new
  WHERE geom IS NULL;
  IF null_geom > 0 THEN
    RAISE EXCEPTION 'Sanity check failed: % rows have NULL geom', null_geom;
  END IF;

  --Invalid geometries should be zero
  SELECT COUNT(*) INTO invalid_geom
  FROM macrostrat.strat_name_footprints_new
  WHERE NOT ST_IsValid(geom) AND ST_AsText(geom) != 'POLYGON EMPTY';
  IF invalid_geom > 0 THEN
    RAISE EXCEPTION 'Sanity check failed: % rows have invalid geometries', invalid_geom;
  END IF;

  --Warn if empty geometries exceed 20%
  SELECT COUNT(*) INTO empty_geom
  FROM macrostrat.strat_name_footprints_new
  WHERE ST_IsEmpty(geom);
  IF empty_geom > new_count * 0.2 THEN
    RAISE WARNING '% of % rows have empty geometries (exceeds 20%%)', empty_geom, new_count;
  END IF;

  RAISE NOTICE 'Sanity checks passed: % rows, % empty geoms, % invalid geoms',
    new_count, empty_geom, invalid_geom;
END $$;

BEGIN;
  ALTER TABLE IF EXISTS macrostrat.strat_name_footprints RENAME TO strat_name_footprints_old;
  ALTER TABLE macrostrat.strat_name_footprints_new RENAME TO strat_name_footprints;
COMMIT;