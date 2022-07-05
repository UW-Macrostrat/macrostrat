CREATE SCHEMA IF NOT EXISTS tile_layers;

CREATE OR REPLACE VIEW tile_layers.carto_units AS
SELECT
  map_id,
  source_id,
  geom,
  'tiny' scale
FROM
  carto_new.tiny
UNION ALL
SELECT
  map_id,
  source_id,
  geom,
  'small' scale
FROM
  carto_new.small
UNION ALL
SELECT
  map_id,
  source_id,
  geom,
  'medium' scale
FROM
  carto_new.medium
UNION ALL
SELECT
  map_id,
  source_id,
  geom,
  'large' scale
FROM carto_new.large;

CREATE OR REPLACE VIEW tile_layers.line_data AS
SELECT
  line_id,
  descrip::text AS descrip,
  name::text AS name,
  new_direction::text AS direction,
  new_type::text AS "type",
  'tiny' scale
FROM lines.tiny
UNION ALL
SELECT
  line_id,
  descrip::text AS descrip,
  name::text AS name,
  new_direction::text AS direction,
  new_type::text AS "type",
  'small' scale
FROM lines.small
UNION ALL
SELECT
  line_id,
  descrip::text AS descrip,
  name::text AS name,
  new_direction::text AS direction,
  new_type::text AS "type",
  'medium' scale
FROM lines.medium
UNION ALL
SELECT
  line_id,
  descrip::text AS descrip,
  name::text AS name,
  new_direction::text AS direction,
  new_type::text AS "type",
  'large' scale
FROM lines.large;

CREATE OR REPLACE VIEW tile_layers.carto_lines AS
SELECT
  x.line_id,
  x.source_id,
  x.geom,
  'tiny' scale
FROM carto_new.lines_tiny x
UNION ALL
SELECT
  x.line_id,
  x.source_id,
  x.geom,
  'small' scale
FROM carto_new.lines_small x
UNION ALL
SELECT
  x.line_id,
  x.source_id,
  x.geom,
  'medium' scale
FROM carto_new.lines_medium x
UNION ALL
SELECT
  x.line_id,
  x.source_id,
  x.geom,
  'large' scale
FROM carto_new.lines_large x;

CREATE OR REPLACE FUNCTION tile_layers.carto_slim(
  -- bounding box
  x integer,
  y integer,
  z integer,
  -- additional parameters
  query_params json
)
RETURNS bytea
AS $$
DECLARE
srid integer;
features record;
mapsize text;
linesize text[];
mercator_bbox geometry;
projected_bbox geometry;
bedrock bytea;
lines bytea;
BEGIN

mercator_bbox := tile_utils.envelope(x, y, z);

projected_bbox := ST_Transform(
  mercator_bbox,
  4326
);

IF z < 3 THEN
  -- Select from carto.tiny table
  mapsize := 'tiny';
  linesize := ARRAY['tiny'];
ELSIF z < 6 THEN
  mapsize := 'small';
  linesize := ARRAY['tiny', 'small'];
ELSIF z < 9 THEN
  mapsize := 'medium';
  linesize := ARRAY['small', 'medium'];
ELSE
  mapsize := 'large';
  linesize := ARRAY['medium', 'large'];
END IF;

-- Units
WITH mvt_features AS (
  SELECT
    map_id,
    source_id,
    ST_AsMVTGeom(
      ST_Transform(geom, 3857),
      mercator_bbox,
      4096
    ) geom
  FROM
    tile_layers.carto_units
  WHERE scale = mapsize AND ST_Intersects(geom, projected_bbox)
), expanded AS (
  SELECT
    z.map_id,
    z.source_id,
    l.legend_id,
    l.best_age_top :: numeric AS best_age_top,
    l.best_age_bottom :: numeric AS best_age_bottom,
    coalesce(l.color, '#777777') AS color,
    l.lith_classes [1] AS lith_class1,
    l.lith_classes [2] AS lith_class2,
    l.lith_classes [3] AS lith_class3,
    l.lith_types [1] AS lith_type1,
    l.lith_types [2] AS lith_type2,
    l.lith_types [3] AS lith_type3,
    l.lith_types [4] AS lith_type4,
    l.lith_types [5] AS lith_type5,
    l.lith_types [6] AS lith_type6,
    l.lith_types [7] AS lith_type7,
    l.lith_types [8] AS lith_type8,
    l.lith_types [9] AS lith_type9,
    l.lith_types [10] AS lith_type10,
    l.lith_types [11] AS lith_type11,
    l.lith_types [12] AS lith_type12,
    l.lith_types [13] AS lith_type13,
    l.all_lith_classes [1] AS lith_class1,
    l.all_lith_classes [2] AS lith_class2,
    l.all_lith_classes [3] AS lith_class3,
    l.all_lith_types [1] AS lith_type1,
    l.all_lith_types [2] AS lith_type2,
    l.all_lith_types [3] AS lith_type3,
    l.all_lith_types [4] AS lith_type4,
    l.all_lith_types [5] AS lith_type5,
    l.all_lith_types [6] AS lith_type6,
    l.all_lith_types [7] AS lith_type7,
    l.all_lith_types [8] AS lith_type8,
    l.all_lith_types [9] AS lith_type9,
    l.all_lith_types [10] AS lith_type10,
    l.all_lith_types [11] AS lith_type11,
    l.all_lith_types [12] AS lith_type12,
    l.all_lith_types [13] AS lith_type13,
    ST_Simplify(z.geom, 2) AS geom
  FROM
    mvt_features z
    LEFT JOIN maps.map_legend ON z.map_id = map_legend.map_id
    LEFT JOIN maps.legend AS l ON l.legend_id = map_legend.legend_id
    LEFT JOIN maps.sources ON l.source_id = sources.source_id
  WHERE
    sources.status_code = 'active'
    AND ST_Area(geom) > 2
)
SELECT
  ST_AsMVT(expanded, 'units')
INTO bedrock
FROM expanded;

-- LINES
WITH mvt_features AS (
  SELECT
    line_id,
    source_id,
    ST_AsMVTGeom(
      ST_Transform(geom, 3857),
      mercator_bbox,
      4096
    ) geom
  FROM
    tile_layers.carto_lines
  WHERE
    scale = mapsize
    AND ST_Intersects(geom, projected_bbox)
),
expanded AS (
  SELECT
    z.line_id,
    z.source_id,
    coalesce(q.descrip, '') AS descrip,
    coalesce(q.name, '') AS name,
    coalesce(q.direction, '') AS direction,
    coalesce(q.type, '') AS "type",
    ST_Simplify(z.geom, 2) AS geom
  FROM mvt_features z
  LEFT JOIN tile_layers.line_data q
    ON z.line_id = q.line_id
  LEFT JOIN maps.sources
    ON z.source_id = sources.source_id
  WHERE sources.status_code = 'active'
    AND q.scale = ANY(linesize)
    AND ST_Length(geom) > 2
)
SELECT
  ST_AsMVT(expanded, 'lines') INTO lines
FROM expanded;

RETURN bedrock || lines;

END;
$$ LANGUAGE plpgsql IMMUTABLE;