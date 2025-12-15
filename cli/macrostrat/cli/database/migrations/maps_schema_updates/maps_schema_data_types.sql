
ALTER TABLE maps.polygons DETACH PARTITION maps.polygons_large;
ALTER TABLE maps.polygons DETACH PARTITION maps.polygons_medium;
ALTER TABLE maps.polygons DETACH PARTITION maps.polygons_small;
ALTER TABLE maps.polygons DETACH PARTITION maps.polygons_tiny;

ALTER TABLE maps.lines DETACH PARTITION maps.lines_large;
ALTER TABLE maps.lines DETACH PARTITION maps.lines_medium;
ALTER TABLE maps.lines DETACH PARTITION maps.lines_small;
ALTER TABLE maps.lines DETACH PARTITION maps.lines_tiny;

drop view if exists points.points;
drop view if exists tile_layers.map_units;
drop view if exists tile_layers.map_lines;

drop view if exists maps.large;
drop view if exists lines.large;
drop view if exists maps.medium;
drop view if exists lines.medium;
drop view if exists maps.small;
drop view if exists lines.small;
drop view if exists maps.tiny;
drop view if exists lines.tiny;

ALTER TABLE maps.polygons
  ALTER COLUMN orig_id TYPE text
  USING orig_id::text;

ALTER TABLE maps.points
  ALTER COLUMN orig_id TYPE text
  USING orig_id::text;

ALTER TABLE maps.lines
  ALTER COLUMN orig_id TYPE text
  USING orig_id::text;

ALTER TABLE maps.polygons_large
  ALTER COLUMN orig_id TYPE text
  USING orig_id::text;

ALTER TABLE maps.lines_large
  ALTER COLUMN orig_id TYPE text
  USING orig_id::text;

ALTER TABLE maps.polygons_medium
  ALTER COLUMN orig_id TYPE text
  USING orig_id::text;

ALTER TABLE maps.lines_medium
  ALTER COLUMN orig_id TYPE text
  USING orig_id::text;

ALTER TABLE maps.polygons_small
  ALTER COLUMN orig_id TYPE text
  USING orig_id::text;

ALTER TABLE maps.lines_small
  ALTER COLUMN orig_id TYPE text
  USING orig_id::text;

ALTER TABLE maps.polygons_tiny
  ALTER COLUMN orig_id TYPE text
  USING orig_id::text;

ALTER TABLE maps.lines_tiny
  ALTER COLUMN orig_id TYPE text
  USING orig_id::text;

ALTER TABLE maps.polygons
  ATTACH PARTITION maps.polygons_large FOR VALUES IN ('large');

ALTER TABLE maps.polygons
  ATTACH PARTITION maps.polygons_medium FOR VALUES IN ('medium');

ALTER TABLE maps.polygons
  ATTACH PARTITION maps.polygons_small FOR VALUES IN ('small');

ALTER TABLE maps.polygons
  ATTACH PARTITION maps.polygons_tiny FOR VALUES IN ('tiny');

ALTER TABLE maps.lines
  ATTACH PARTITION maps.lines_large FOR VALUES IN ('large');

ALTER TABLE maps.lines
  ATTACH PARTITION maps.lines_medium FOR VALUES IN ('medium');

ALTER TABLE maps.lines
  ATTACH PARTITION maps.lines_small FOR VALUES IN ('small');

ALTER TABLE maps.lines
  ATTACH PARTITION maps.lines_tiny FOR VALUES IN ('tiny');

