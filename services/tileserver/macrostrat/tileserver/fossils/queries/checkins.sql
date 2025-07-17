WITH tile AS (
  SELECT ST_TileEnvelope(:z, :x, :y) AS envelope
), collections AS (
  SELECT
    collection_no AS id,
    collection_no AS collection,
    ST_AsMVTGeom(
      ST_Transform(ST_SetSRID(geom, 4326), 3857),
      tile.envelope
    ) AS geom
  FROM macrostrat.pbdb_collections, tile
  WHERE geom IS NOT NULL
    AND ST_Intersects(
      ST_SetSRID(geom, 4326),
      ST_Transform(tile.envelope, 4326)
    )
)
SELECT ST_AsMVT(collections, 'default') AS mvt FROM collections;
