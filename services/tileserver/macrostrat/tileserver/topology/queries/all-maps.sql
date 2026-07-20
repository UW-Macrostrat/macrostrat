WITH tile AS (
  SELECT
    ST_TileEnvelope(:z, :x, :y) AS mercator_bbox,
    tile_layers.geographic_envelope(:x, :y, :z, 0.01) AS projected_envelope
), sources AS (
  SELECT
    s.source_id,
    s.name,
    s.slug,
    scale,
    tile_layers.tile_geom(
     ST_Intersection(geometry, projected_envelope),
      mercator_bbox
    ) AS geom
  FROM map_bounds.map_area ma
  JOIN tile
    ON ST_Intersects(geometry, projected_envelope)
  JOIN maps.sources s
    ON ma.id = s.source_id
)
SELECT ST_AsMVT(sources, 'maps', 4096, 'geom') FROM sources;
