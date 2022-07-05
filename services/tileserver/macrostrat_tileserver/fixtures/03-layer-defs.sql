CREATE SCHEMA IF NOT EXISTS tile_layers;

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
mercator_bbox geometry;
projected_bbox geometry;
bedrock bytea;
BEGIN

mercator_bbox := tile_utils.envelope(x, y, z);

projected_bbox := ST_Transform(
  mercator_bbox,
  4326
);


WITH a AS (
SELECT
  map_id,
  source_id,
  ST_Simplify(
    ST_AsMVTGeom(
      ST_Transform(geom, 3857),
      mercator_bbox,
      4096
    ),
    1
  ) geom
FROM
  carto_new.tiny
WHERE
  ST_Intersects(geom, projected_bbox)
)
SELECT
  ST_AsMVT(a) INTO bedrock
FROM a;

RETURN bedrock;
END;
$$ LANGUAGE plpgsql IMMUTABLE;