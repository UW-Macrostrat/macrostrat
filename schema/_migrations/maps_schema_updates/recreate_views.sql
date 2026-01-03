CREATE TYPE macrostrat.map_scale AS ENUM (
    'tiny',
    'small',
    'medium',
    'large'
);

CREATE OR REPLACE VIEW maps.large as
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

CREATE OR REPLACE VIEW maps.medium AS
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

CREATE OR REPLACE VIEW maps.small AS
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

CREATE OR REPLACE VIEW maps.tiny AS
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


CREATE OR REPLACE VIEW lines.large AS
  SELECT lines.line_id,
    lines.orig_id,
    lines.source_id,
    lines.name,
    lines.type_legacy AS type,
    lines.direction_legacy AS direction,
    lines.descrip,
    lines.geom,
    lines.type AS new_type,
    lines.direction AS new_direction
   FROM maps.lines
  WHERE lines.scale = 'large'::maps.map_scale;

CREATE OR REPLACE VIEW lines.medium AS
  SELECT lines.line_id,
    lines.orig_id,
    lines.source_id,
    lines.name,
    lines.type_legacy AS type,
    lines.direction_legacy AS direction,
    lines.descrip,
    lines.geom,
    lines.type AS new_type,
    lines.direction AS new_direction
   FROM maps.lines
  WHERE lines.scale = 'medium'::maps.map_scale;

CREATE OR REPLACE VIEW lines.small AS
 SELECT lines.line_id,
    lines.orig_id,
    lines.source_id,
    lines.name,
    lines.type_legacy AS type,
    lines.direction_legacy AS direction,
    lines.descrip,
    lines.geom,
    lines.type AS new_type,
    lines.direction AS new_direction
   FROM maps.lines
  WHERE lines.scale = 'small'::maps.map_scale;

CREATE OR REPLACE VIEW lines.tiny AS
  SELECT lines.line_id,
    lines.orig_id,
    lines.source_id,
    lines.name,
    lines.type_legacy AS type,
    lines.direction_legacy AS direction,
    lines.descrip,
    lines.geom,
    lines.type AS new_type,
    lines.direction AS new_direction
   FROM maps.lines
  WHERE lines.scale = 'tiny'::maps.map_scale;

CREATE OR REPLACE VIEW tile_layers.map_units AS
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

CREATE OR REPLACE VIEW points.points AS
 SELECT points.source_id,
    points.strike,
    points.dip,
    points.dip_dir,
    points.point_type,
    points.certainty,
    points.comments,
    points.geom,
    points.point_id,
    points.orig_id
   FROM maps.points;

CREATE OR REPLACE VIEW tile_layers.map_lines AS
 SELECT lines.line_id,
    lines.orig_id,
    lines.source_id,
    lines.name,
    lines.type_legacy,
    lines.direction_legacy,
    lines.descrip,
    lines.geom,
    lines.type,
    lines.direction,
    lines.scale
   FROM maps.lines;