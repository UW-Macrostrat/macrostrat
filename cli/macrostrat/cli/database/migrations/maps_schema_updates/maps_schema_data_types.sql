
ALTER TABLE maps.polygons DETACH PARTITION maps.polygons_large;
ALTER TABLE maps.polygons DETACH PARTITION maps.polygons_medium;
ALTER TABLE maps.polygons DETACH PARTITION maps.polygons_small;
ALTER TABLE maps.polygons DETACH PARTITION maps.polygons_tiny;

ALTER TABLE maps.polygons
  ALTER COLUMN orig_id TYPE text
  USING orig_id::text;

drop view if exists tile_layers.map_units;
drop view if exists maps.large;

ALTER TABLE maps.polygons_large
  ALTER COLUMN orig_id TYPE text
  USING orig_id::text;

drop view if exists maps.medium;

ALTER TABLE maps.polygons_medium
  ALTER COLUMN orig_id TYPE text
  USING orig_id::text;

drop view if exists maps.small;

ALTER TABLE maps.polygons_small
  ALTER COLUMN orig_id TYPE text
  USING orig_id::text;


drop view if exists maps.tiny;

ALTER TABLE maps.polygons_tiny
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

CREATE VIEW IF NOT EXISTS maps.large as
 SELECT polygons_large.map_id,
    polygons_large.orig_id,
    polygons_large.source_id,
    polygons_large.name,
    polygons_large.strat_name,
    polygons_large.age,
    polygons_large.lith,
    polygons_large.descrip,
    polygons_large.comments,
    polygons_large.t_interval,
    polygons_large.b_interval,
    polygons_large.geom
   FROM maps.polygons_large;

CREATE VIEW IF NOT EXISTS maps.medium AS
 SELECT polygons_medium.map_id,
    polygons_medium.orig_id,
    polygons_medium.source_id,
    polygons_medium.name,
    polygons_medium.strat_name,
    polygons_medium.age,
    polygons_medium.lith,
    polygons_medium.descrip,
    polygons_medium.comments,
    polygons_medium.t_interval,
    polygons_medium.b_interval,
    polygons_medium.geom
   FROM maps.polygons_medium;

CREATE VIEW IF NOT EXISTS maps.small AS
 SELECT polygons_small.map_id,
    polygons_small.orig_id,
    polygons_small.source_id,
    polygons_small.name,
    polygons_small.strat_name,
    polygons_small.age,
    polygons_small.lith,
    polygons_small.descrip,
    polygons_small.comments,
    polygons_small.t_interval,
    polygons_small.b_interval,
    polygons_small.geom
   FROM maps.polygons_small;

CREATE VIEW IF NOT EXISTS maps.tiny AS
 SELECT polygons_tiny.map_id,
    polygons_tiny.orig_id,
    polygons_tiny.source_id,
    polygons_tiny.name,
    polygons_tiny.strat_name,
    polygons_tiny.age,
    polygons_tiny.lith,
    polygons_tiny.descrip,
    polygons_tiny.comments,
    polygons_tiny.t_interval,
    polygons_tiny.b_interval,
    polygons_tiny.geom
   FROM maps.polygons_tiny;


CREATE VIEW IF NOT EXISTS tile_layers.map_units AS
 SELECT tiny.map_id,
    tiny.orig_id,
    tiny.source_id,
    tiny.name,
    tiny.strat_name,
    tiny.age,
    tiny.lith,
    tiny.descrip,
    tiny.comments,
    tiny.t_interval,
    tiny.b_interval,
    tiny.geom,
    'tiny'::text AS scale
   FROM maps.tiny
UNION ALL
 SELECT small.map_id,
    small.orig_id,
    small.source_id,
    small.name,
    small.strat_name,
    small.age,
    small.lith,
    small.descrip,
    small.comments,
    small.t_interval,
    small.b_interval,
    small.geom,
    'small'::text AS scale
   FROM maps.small
UNION ALL
 SELECT medium.map_id,
    medium.orig_id,
    medium.source_id,
    medium.name,
    medium.strat_name,
    medium.age,
    medium.lith,
    medium.descrip,
    medium.comments,
    medium.t_interval,
    medium.b_interval,
    medium.geom,
    'medium'::text AS scale
   FROM maps.medium
UNION ALL
 SELECT large.map_id,
    large.orig_id,
    large.source_id,
    large.name,
    large.strat_name,
    large.age,
    large.lith,
    large.descrip,
    large.comments,
    large.t_interval,
    large.b_interval,
    large.geom,
    'large'::text AS scale
   FROM maps.large;
