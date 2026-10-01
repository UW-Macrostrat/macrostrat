/* Flatten `maps.polygons`: one table, `scale` an ordinary indexed column.
   Rationale and measurements are in the workbench vault,
   `Design/Map polygon partitioning`.

   Runs as one transaction (see `__init__.py`), so a failure anywhere leaves the
   partitioned table untouched. The rows are not copied twice over -- the
   largest partition becomes the flat table and the other three are merged into
   it, scale by scale, so the heap stays clustered by scale. */

ALTER TABLE maps.polygons DETACH PARTITION maps.polygons_large;
ALTER TABLE maps.polygons DETACH PARTITION maps.polygons_medium;
ALTER TABLE maps.polygons DETACH PARTITION maps.polygons_small;
ALTER TABLE maps.polygons DETACH PARTITION maps.polygons_tiny;

/* Point the per-scale views at the table that will survive before anything is
   dropped, so nothing above them (`tile_layers.map_units`) cascades. Replaced
   again below with their final definition, once the table has its final name. */
CREATE OR REPLACE VIEW maps.medium AS
SELECT map_id, orig_id, source_id, name, strat_name, age, lith, descrip, comments,
  t_interval, b_interval, geom
FROM maps.polygons_large WHERE scale = 'medium';
CREATE OR REPLACE VIEW maps.small AS
SELECT map_id, orig_id, source_id, name, strat_name, age, lith, descrip, comments,
  t_interval, b_interval, geom
FROM maps.polygons_large WHERE scale = 'small';
CREATE OR REPLACE VIEW maps.tiny AS
SELECT map_id, orig_id, source_id, name, strat_name, age, lith, descrip, comments,
  t_interval, b_interval, geom
FROM maps.polygons_large WHERE scale = 'tiny';

/* The empty parent. Its dependents go with it -- functions declared to return
   its row type (`map_bounds.polygons_of`) -- and are restored by the chunk sync
   that follows this migration. */
DROP TABLE maps.polygons CASCADE;

ALTER TABLE maps.polygons_large RENAME TO polygons;

/* Shed what made it a partition. The index set is rebuilt after the merge, so
   the bulk insert does not maintain six indexes row by row. */
DO $$
DECLARE
  _name text;
BEGIN
  SELECT conname INTO _name FROM pg_constraint
  WHERE conrelid = 'maps.polygons'::regclass AND contype = 'p';
  EXECUTE 'ALTER TABLE maps.polygons DROP CONSTRAINT ' || quote_ident(_name);
  FOR _name IN
    SELECT indexname FROM pg_indexes
    WHERE schemaname = 'maps' AND tablename = 'polygons'
  LOOP
    EXECUTE 'DROP INDEX maps.' || quote_ident(_name);
  END LOOP;
END
$$;
ALTER TABLE maps.polygons DROP CONSTRAINT polygons_large_scale_check;
ALTER TABLE maps.polygons DROP CONSTRAINT IF EXISTS enforce_valid_geom_large;
ALTER TABLE maps.polygons ALTER COLUMN scale DROP DEFAULT;

/* Merge, one scale at a time and in map order, so the heap is clustered by
   scale and then by source. */
INSERT INTO maps.polygons (map_id, orig_id, source_id, name, strat_name, age, lith,
  descrip, comments, t_interval, b_interval, geom, scale)
SELECT map_id, orig_id, source_id, name, strat_name, age, lith,
  descrip, comments, t_interval, b_interval, geom, scale
FROM maps.polygons_medium ORDER BY source_id, map_id;
INSERT INTO maps.polygons (map_id, orig_id, source_id, name, strat_name, age, lith,
  descrip, comments, t_interval, b_interval, geom, scale)
SELECT map_id, orig_id, source_id, name, strat_name, age, lith,
  descrip, comments, t_interval, b_interval, geom, scale
FROM maps.polygons_small ORDER BY source_id, map_id;
INSERT INTO maps.polygons (map_id, orig_id, source_id, name, strat_name, age, lith,
  descrip, comments, t_interval, b_interval, geom, scale)
SELECT map_id, orig_id, source_id, name, strat_name, age, lith,
  descrip, comments, t_interval, b_interval, geom, scale
FROM maps.polygons_tiny ORDER BY source_id, map_id;

DROP TABLE maps.polygons_medium;
DROP TABLE maps.polygons_small;
DROP TABLE maps.polygons_tiny;

/* The key the partitioning could not declare. Fails here if two scales ever
   issued the same id, which is exactly the thing worth knowing. */
ALTER TABLE maps.polygons ADD CONSTRAINT maps_polygons_pkey PRIMARY KEY (map_id);

/* One sequence. `public.map_ids` is the live one -- the partitions drew from it
   -- and `maps.map_ids`, the parent's default, drifted behind it. The live one
   moves into the schema under the name the table already used. */
DROP SEQUENCE maps.map_ids;
ALTER SEQUENCE public.map_ids SET SCHEMA maps;
ALTER SEQUENCE maps.map_ids OWNED BY maps.polygons.map_id;
ALTER TABLE maps.polygons ALTER COLUMN map_id SET DEFAULT nextval('maps.map_ids');
SELECT setval('maps.map_ids', greatest(last_value, (SELECT max(map_id) FROM maps.polygons)))
FROM maps.map_ids;

/* The index set. `(scale, geom)` is the partition pruning the table used to get
   for free, now inside one index -- a request for one scale descends only that
   scale's subtree, however the predicate is written. The btree on `(scale,
   source_id)` is what the heap is clustered on. */
CREATE INDEX polygons_scale_geom_idx ON maps.polygons USING gist (scale, geom);
CREATE INDEX polygons_scale_source_id_idx ON maps.polygons USING btree (scale, source_id);
CREATE INDEX polygons_source_id_idx ON maps.polygons USING btree (source_id);
CREATE INDEX polygons_orig_id_idx ON maps.polygons USING btree (orig_id);
CREATE INDEX polygons_name_idx ON maps.polygons USING btree (name);
CREATE INDEX polygons_t_interval_idx ON maps.polygons USING btree (t_interval);
CREATE INDEX polygons_b_interval_idx ON maps.polygons USING btree (b_interval);
ALTER TABLE maps.polygons CLUSTER ON polygons_scale_source_id_idx;

/* The old partitions, as views. Writable, with the scale each one implied, so an
   insert that named a partition still lands where it did. */
CREATE VIEW maps.polygons_large AS
  SELECT * FROM maps.polygons WHERE scale = 'large' WITH CHECK OPTION;
CREATE VIEW maps.polygons_medium AS
  SELECT * FROM maps.polygons WHERE scale = 'medium' WITH CHECK OPTION;
CREATE VIEW maps.polygons_small AS
  SELECT * FROM maps.polygons WHERE scale = 'small' WITH CHECK OPTION;
CREATE VIEW maps.polygons_tiny AS
  SELECT * FROM maps.polygons WHERE scale = 'tiny' WITH CHECK OPTION;
ALTER VIEW maps.polygons_large ALTER COLUMN scale SET DEFAULT 'large';
ALTER VIEW maps.polygons_medium ALTER COLUMN scale SET DEFAULT 'medium';
ALTER VIEW maps.polygons_small ALTER COLUMN scale SET DEFAULT 'small';
ALTER VIEW maps.polygons_tiny ALTER COLUMN scale SET DEFAULT 'tiny';
COMMENT ON VIEW maps.polygons_large IS 'Compatibility view over maps.polygons, which was partitioned by scale. New code reads and writes maps.polygons.';
COMMENT ON VIEW maps.polygons_medium IS 'Compatibility view over maps.polygons, which was partitioned by scale. New code reads and writes maps.polygons.';
COMMENT ON VIEW maps.polygons_small IS 'Compatibility view over maps.polygons, which was partitioned by scale. New code reads and writes maps.polygons.';
COMMENT ON VIEW maps.polygons_tiny IS 'Compatibility view over maps.polygons, which was partitioned by scale. New code reads and writes maps.polygons.';

CREATE OR REPLACE VIEW maps.large AS
SELECT map_id, orig_id, source_id, name, strat_name, age, lith, descrip, comments,
  t_interval, b_interval, geom
FROM maps.polygons WHERE scale = 'large';
CREATE OR REPLACE VIEW maps.medium AS
SELECT map_id, orig_id, source_id, name, strat_name, age, lith, descrip, comments,
  t_interval, b_interval, geom
FROM maps.polygons WHERE scale = 'medium';
CREATE OR REPLACE VIEW maps.small AS
SELECT map_id, orig_id, source_id, name, strat_name, age, lith, descrip, comments,
  t_interval, b_interval, geom
FROM maps.polygons WHERE scale = 'small';
CREATE OR REPLACE VIEW maps.tiny AS
SELECT map_id, orig_id, source_id, name, strat_name, age, lith, descrip, comments,
  t_interval, b_interval, geom
FROM maps.polygons WHERE scale = 'tiny';

/* The references that could not be declared against a partitioned table.
   `NOT VALID`, because deleting polygons never reached these tables and left
   orphans behind; from here a polygon takes its derived rows with it. Validate
   once the orphans are cleared (`VALIDATE CONSTRAINT`). */
ALTER TABLE maps.map_legend ADD CONSTRAINT map_legend_map_id_fkey
  FOREIGN KEY (map_id) REFERENCES maps.polygons (map_id) ON DELETE CASCADE NOT VALID;
ALTER TABLE maps.map_units ADD CONSTRAINT map_units_map_id_fkey
  FOREIGN KEY (map_id) REFERENCES maps.polygons (map_id) ON DELETE CASCADE NOT VALID;
ALTER TABLE maps.map_liths ADD CONSTRAINT map_liths_map_id_fkey
  FOREIGN KEY (map_id) REFERENCES maps.polygons (map_id) ON DELETE CASCADE NOT VALID;

ANALYZE maps.polygons;
