WITH
tile AS (
  SELECT ST_TileEnvelope(:z, :x, :y) AS envelope,
         tile_layers.geographic_envelope(:x, :y, :z, 0.01) AS envelope_4326
),
collections AS (
  SELECT
    collection_no,
    name,
    tile_layers.tile_geom(
      ST_Intersection(geom, envelope_4326),
      envelope
    ) AS geom
  FROM macrostrat.pbdb_collections, tile
  WHERE
    geom IS NOT NULL
    AND ST_Intersects(geom, envelope_4326)
)

SELECT ST_AsMVT(
  collections.*,
  'default',
  4096,
  'geom'
) AS mvt
FROM collections;
