CREATE SCHEMA IF NOT EXISTS tile_layers;

CREATE OR REPLACE VIEW tile_layers.carto_data AS
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


CREATE OR REPLACE FUNCTION tile_layers.carto(
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
mercator_bbox geometry;
projected_bbox geometry;
bedrock bytea;
BEGIN

mercator_bbox := tile_utils.envelope(x, y, z);

projected_bbox := ST_Transform(
  mercator_bbox,
  4326
);

IF z < 3 THEN
  -- Select from carto.tiny table
  mapsize := 'tiny';
ELSIF z < 6 THEN
  mapsize := 'small';
ELSIF z < 9 THEN
  mapsize := 'medium';
ELSE
  mapsize := 'large';
END IF;

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
    tile_layers.carto_data
  WHERE scale = mapsize AND ST_Intersects(geom, projected_bbox)
), a AS (
  SELECT
    map_id,
    source_id,
    ST_Simplify(geom, 2) geom
  FROM mvt_features
  WHERE ST_Area(geom) > 2
)
SELECT
  ST_AsMVT(a) INTO bedrock
FROM
  a;

RETURN bedrock;

END;
$$ LANGUAGE plpgsql IMMUTABLE;