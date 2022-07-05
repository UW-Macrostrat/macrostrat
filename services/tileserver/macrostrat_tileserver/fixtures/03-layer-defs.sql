CREATE SCHEMA IF NOT EXISTS tile_layers;

CREATE OR REPLACE FUNCTION tile_layers.carto(
  -- bounding box
  _xmin float,
  _ymin float,
  _xmax float,
  _ymax float,
  -- EPSG (SRID) of the bounding box coordinates
  epsg integer,
  -- additional parameters
  query_params json
)
RETURNS bytea
AS $$
DECLARE
srid integer;
mercator_bbox geometry;
projected_bbox geometry;
bedrock bytea;
BEGIN

mercator_bbox := ST_MakeEnvelope(
  _xmin,
  _ymin,
  _xmax,
  _ymax,
  -- If EPSG is null we set it to 0
  epsg
);

projected_bbox := ST_Transform(
  mercator_bbox,
  4326
);

SELECT
  ST_AsMVT(a) INTO bedrock
FROM
  (
    SELECT
      map_id,
      source_id,
      ST_Simplify(
        ST_AsMVTGeom(
          ST_Transform(geom, 3857),
          mercator_bbox,
          4096
        ), 1
      ) geom
    FROM
      carto_new.tiny
    WHERE
      ST_Intersects(geom, projected_bbox)
  ) a;

RETURN bedrock;
END;
$$ LANGUAGE plpgsql IMMUTABLE;