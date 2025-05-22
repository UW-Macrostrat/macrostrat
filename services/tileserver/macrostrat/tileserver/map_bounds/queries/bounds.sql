WITH tile AS (
  SELECT ST_TileEnvelope(:z, :x, :y) AS envelope,
         tile_layers.geographic_envelope(:x, :y, :z, 0.01) AS envelope_4326

), sources AS (
  SELECT
    source_id,
    is_finalized,
    name,
    slug,
    scale,
    tile_layers.tile_geom(
     ST_Intersection(rgeom, envelope_4326),
      envelope
    ) AS geom
  FROM maps.sources, tile
  WHERE
    rgeom is NOT NULL
    AND :where
    AND ST_Intersects(rgeom, envelope_4326)
)
SELECT * FROM sources z
WHERE z.geom IS NOT NULL;
