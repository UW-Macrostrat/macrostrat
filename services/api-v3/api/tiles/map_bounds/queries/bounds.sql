-- Maps only: a compilation's bounds would cover its members'. A mosaic is a map.
WITH tile AS (
  SELECT ST_TileEnvelope(:z, :x, :y) AS envelope,
         tile_layers.geographic_envelope(:x, :y, :z, 0.01) AS envelope_4326

-- Ids only, materialized: the clip runs on passing sources, without copying geometry.
), passing AS MATERIALIZED (
  SELECT s.source_id
  FROM maps.sources s
  JOIN map_bounds.map_area a ON a.id = s.source_id, tile
  WHERE
    :where
    AND a.geometry && envelope_4326
    AND NOT (
      map_bounds.is_compilation(s.source_id)
      AND NOT map_bounds.is_mosaic(s.source_id)
    )
), sources AS (
  SELECT
    s.source_id,
    is_finalized,
    name,
    slug,
    scale,
    tile_layers.tile_geom(
     ST_Intersection(a.geometry, envelope_4326),
      envelope
    ) AS geom
  FROM passing p
  JOIN maps.sources s ON s.source_id = p.source_id
  JOIN map_bounds.map_area a ON a.id = p.source_id, tile
  WHERE ST_Intersects(a.geometry, envelope_4326)
)
SELECT * FROM sources z
WHERE z.geom IS NOT NULL;
