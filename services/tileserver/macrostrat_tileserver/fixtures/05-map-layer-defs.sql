/* This view is a stopgap to prepare for a unified tablespace for map units */
CREATE OR REPLACE VIEW tile_layers.map_units AS
SELECT
  *,
  'tiny' scale
FROM maps.tiny
UNION ALL
SELECT
  *,
  'small' scale
FROM maps.small
UNION ALL
SELECT
  *,
  'medium' scale
FROM maps.medium
UNION ALL
SELECT
  *,
  'large' scale
FROM maps.large;

CREATE OR REPLACE VIEW tile_layers.map_lines AS
SELECT
  *,
  'tiny' scale
FROM lines.tiny
UNION ALL
SELECT
  *,
  'small' scale
FROM lines.small
UNION ALL
SELECT
  *,
  'medium' scale
FROM lines.medium
UNION ALL
SELECT
  *,
  'large' scale
FROM lines.large;

CREATE OR REPLACE FUNCTION tile_layers.map(
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
_source_id integer;
mercator_bbox geometry;
projected_bbox geometry;
bedrock bytea;
lines bytea;
tolerance double precision;
BEGIN

-- Get the map id requested from the query params
_source_id := (query_params->>'source_id')::integer;

IF _source_id IS NULL THEN
  RAISE EXCEPTION 'source_id is required';
END IF;

mercator_bbox := tile_utils.envelope(x, y, z);
tolerance := 6;

projected_bbox := ST_Transform(
  mercator_bbox,
  4326
);

-- Get map size
SELECT scale
  FROM tile_layers.map_units
 WHERE source_id = _source_id
 LIMIT 1
INTO mapsize;

IF mapsize = 'tiny' THEN
  linesize := ARRAY['tiny'];
ELSIF mapsize = 'small' THEN
  linesize := ARRAY['tiny', 'small'];
ELSIF mapsize = 'medium' THEN
  linesize := ARRAY['small', 'medium'];
ELSE
  linesize := ARRAY['medium', 'large'];
END IF;

-- Units
WITH mvt_features AS (
  SELECT
    map_id,
    source_id,
    geom
  FROM
    tile_layers.map_units
  WHERE source_id = _source_id
    AND ST_Intersects(geom, projected_bbox)
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
    tile_layers.tile_geom(z.geom, mercator_bbox) AS geom
  FROM mvt_features z
    LEFT JOIN maps.map_legend ON z.map_id = map_legend.map_id
    LEFT JOIN maps.legend AS l ON l.legend_id = map_legend.legend_id
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
    geom
  FROM
    tile_layers.map_lines
  WHERE source_id = _source_id
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
    tile_layers.tile_geom(z.geom, mercator_bbox) AS geom
  FROM mvt_features z
  LEFT JOIN tile_layers.line_data q
    ON z.line_id = q.line_id
  WHERE q.scale = ANY(linesize)
    --AND ST_Length(geom) > tolerance
)
SELECT
  ST_AsMVT(expanded, 'lines') INTO lines
FROM expanded;

RETURN bedrock || lines;

END;
$$ LANGUAGE plpgsql IMMUTABLE;
