CREATE SCHEMA IF NOT EXISTS tile_layers;

CREATE OR REPLACE FUNCTION tile_layers.carto(
  -- bounding box
  _xmin float,
  ymin float,
  _xmax float,
  ymax float,
  -- EPSG (SRID) of the bounding box coordinates
  epsg integer,
  -- additional parameters
  query_params json
) RETURNS bytea
AS $$
SELECT
  ST_AsMVT(tile)
FROM
  carto_new.tiny tile
WHERE
  ST_Intersects(
    tile.geom,
    ST_Transform(
      ST_MakeEnvelope(
        _xmin,
        ymin,
        _xmax,
        ymax,
        -- If EPSG is null we set it to 0
        epsg
      ),
      4326
    )
  )
$$ LANGUAGE SQL IMMUTABLE;