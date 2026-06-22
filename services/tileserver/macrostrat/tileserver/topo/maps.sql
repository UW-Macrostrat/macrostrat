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
    mp.priority,
    tile_layers.tile_geom(
     ST_Intersection(geometry, projected_envelope),
      mercator_bbox
    ) AS geom
  FROM map_bounds.map_area ma
  JOIN tile
    ON ST_Intersects(geometry, projected_envelope)
  JOIN maps.sources s
    ON ma.id = s.source_id
  JOIN map_bounds.map_layer ml
    ON ma.map_layer = ml.id
    OR ma.map_layer = ANY(ml.composited_from)
  LEFT JOIN map_bounds.map_priority mp
    ON ma.id = mp.map_id AND mp.map_layer = ml.id
  WHERE ml.slug = :map_layer
)
SELECT ST_AsMVT(sources, 'maps', 4096, 'geom') FROM sources;
