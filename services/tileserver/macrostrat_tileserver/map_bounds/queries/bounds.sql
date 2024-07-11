WITH tile AS (
  SELECT ST_TileEnvelope(:z, :x, :y) AS envelope,
         ST_Transform(ST_TileEnvelope(:z, :x, :y, margin => 0.01), 4326) AS envelope_4326
), sources AS (
  SELECT
    source_id,
    name,
    slug,
    scale,
    rgeom AS geom
  FROM maps.sources
  WHERE
    rgeom is NOT NULL
    AND status_code = 'active'
), features AS (
  SELECT
    source_id,
    name,
    slug,
    scale,
    ST_Intersection(geom, envelope_4326) AS geom
  FROM sources, tile
  WHERE ST_Intersects(geom, ST_Transform(envelope, 4326))
)
SELECT
  source_id,
  name,
  slug,
  scale,
  tile_layers.tile_geom(z.geom, envelope) AS geom
FROM features z, tile
WHERE z.geom IS NOT NULL;
