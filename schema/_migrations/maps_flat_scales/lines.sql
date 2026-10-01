/* Flatten `maps.lines`, the same way as `maps.polygons` (`polygons.sql`): the
   largest partition survives, the rest merge into it in scale order. */

ALTER TABLE maps.lines DETACH PARTITION maps.lines_large;
ALTER TABLE maps.lines DETACH PARTITION maps.lines_medium;
ALTER TABLE maps.lines DETACH PARTITION maps.lines_small;
ALTER TABLE maps.lines DETACH PARTITION maps.lines_tiny;

/* The `lines.<scale>` views and `tile_layers.map_lines` read the parent and go
   with it, as does `map_bounds.lines_of`; the chunk sync restores them. */
DROP TABLE maps.lines CASCADE;

ALTER TABLE maps.lines_large RENAME TO lines;

DO $$
DECLARE
  _name text;
BEGIN
  SELECT conname INTO _name FROM pg_constraint
  WHERE conrelid = 'maps.lines'::regclass AND contype = 'p';
  EXECUTE 'ALTER TABLE maps.lines DROP CONSTRAINT ' || quote_ident(_name);
  FOR _name IN
    SELECT indexname FROM pg_indexes
    WHERE schemaname = 'maps' AND tablename = 'lines'
  LOOP
    EXECUTE 'DROP INDEX maps.' || quote_ident(_name);
  END LOOP;
END
$$;
ALTER TABLE maps.lines DROP CONSTRAINT lines_large_scale_check;
ALTER TABLE maps.lines ALTER COLUMN scale DROP DEFAULT;

INSERT INTO maps.lines (line_id, orig_id, source_id, name, type_legacy, direction_legacy,
  descrip, geom, type, direction, scale)
SELECT line_id, orig_id, source_id, name, type_legacy, direction_legacy,
  descrip, geom, type, direction, scale
FROM maps.lines_medium ORDER BY source_id, line_id;
INSERT INTO maps.lines (line_id, orig_id, source_id, name, type_legacy, direction_legacy,
  descrip, geom, type, direction, scale)
SELECT line_id, orig_id, source_id, name, type_legacy, direction_legacy,
  descrip, geom, type, direction, scale
FROM maps.lines_small ORDER BY source_id, line_id;
INSERT INTO maps.lines (line_id, orig_id, source_id, name, type_legacy, direction_legacy,
  descrip, geom, type, direction, scale)
SELECT line_id, orig_id, source_id, name, type_legacy, direction_legacy,
  descrip, geom, type, direction, scale
FROM maps.lines_tiny ORDER BY source_id, line_id;

DROP TABLE maps.lines_medium;
DROP TABLE maps.lines_small;
DROP TABLE maps.lines_tiny;

ALTER TABLE maps.lines ADD CONSTRAINT lines_pkey PRIMARY KEY (line_id);

/* `public.line_ids` was already the one sequence every partition and the parent
   drew from. It moves into the schema beside `maps.map_ids` and gains an owner. */
ALTER SEQUENCE public.line_ids SET SCHEMA maps;
ALTER SEQUENCE maps.line_ids OWNED BY maps.lines.line_id;
ALTER TABLE maps.lines ALTER COLUMN line_id SET DEFAULT nextval('maps.line_ids');

CREATE INDEX lines_scale_geom_idx ON maps.lines USING gist (scale, geom);
CREATE INDEX lines_scale_source_id_idx ON maps.lines USING btree (scale, source_id);
CREATE INDEX lines_source_id_idx ON maps.lines USING btree (source_id);
CREATE INDEX lines_orig_id_idx ON maps.lines USING btree (orig_id);
ALTER TABLE maps.lines CLUSTER ON lines_scale_source_id_idx;

CREATE VIEW maps.lines_large AS
  SELECT * FROM maps.lines WHERE scale = 'large' WITH CHECK OPTION;
CREATE VIEW maps.lines_medium AS
  SELECT * FROM maps.lines WHERE scale = 'medium' WITH CHECK OPTION;
CREATE VIEW maps.lines_small AS
  SELECT * FROM maps.lines WHERE scale = 'small' WITH CHECK OPTION;
CREATE VIEW maps.lines_tiny AS
  SELECT * FROM maps.lines WHERE scale = 'tiny' WITH CHECK OPTION;
ALTER VIEW maps.lines_large ALTER COLUMN scale SET DEFAULT 'large';
ALTER VIEW maps.lines_medium ALTER COLUMN scale SET DEFAULT 'medium';
ALTER VIEW maps.lines_small ALTER COLUMN scale SET DEFAULT 'small';
ALTER VIEW maps.lines_tiny ALTER COLUMN scale SET DEFAULT 'tiny';
COMMENT ON VIEW maps.lines_large IS 'Compatibility view over maps.lines, which was partitioned by scale. New code reads and writes maps.lines.';
COMMENT ON VIEW maps.lines_medium IS 'Compatibility view over maps.lines, which was partitioned by scale. New code reads and writes maps.lines.';
COMMENT ON VIEW maps.lines_small IS 'Compatibility view over maps.lines, which was partitioned by scale. New code reads and writes maps.lines.';
COMMENT ON VIEW maps.lines_tiny IS 'Compatibility view over maps.lines, which was partitioned by scale. New code reads and writes maps.lines.';

ANALYZE maps.lines;
