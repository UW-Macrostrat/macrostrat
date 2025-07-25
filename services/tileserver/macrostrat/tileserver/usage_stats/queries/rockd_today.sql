WITH
tile AS (
  SELECT ST_TileEnvelope(:z, :x, :y) AS envelope,
         tile_layers.geographic_envelope(:x, :y, :z, 0.01) AS envelope_4326
),
points AS (
  SELECT
    id,
    tile_layers.tile_geom(
      ST_Intersection(
        ST_SetSRID(ST_MakePoint(lng, lat), 4326),
        envelope_4326
      ),
      envelope
    ) AS geom
  FROM usage_stats.rockd_stats, tile
  WHERE
    lat IS NOT NULL AND lng IS NOT NULL
    AND ST_Intersects(
      ST_SetSRID(ST_MakePoint(lng, lat), 4326),
      envelope_4326
    )
    AND date >= (NOW() - INTERVAL '24 hours')
)

SELECT ST_AsMVT(
  points.*,
  'default',
  4096,
  'geom'
) AS mvt
FROM points;