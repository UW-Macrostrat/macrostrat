-- "Regions" are still stored as geologic_boundaries.boundaries.
WITH tile AS (
  SELECT ST_TileEnvelope(:z, :x, :y) AS envelope,
         tile_layers.geographic_envelope(:x, :y, :z, 0.01) AS envelope_4326
)
SELECT
  b.boundary_id AS region_id,
  b.source_id,
  b.name,
  b.boundary_group AS region_group,
  b.boundary_type AS region_type,
  initcap(b.boundary_class) AS region_class,
  -- Box clip tolerates invalid polygons, where ST_Intersection raises.
  tile_layers.tile_geom(ST_ClipByBox2D(b.geom, envelope_4326), envelope) AS geom
FROM geologic_boundaries.boundaries b, tile
WHERE b.geom && envelope_4326
  AND :where
