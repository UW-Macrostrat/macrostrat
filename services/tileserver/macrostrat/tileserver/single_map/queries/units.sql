SELECT
  p.map_id,
  p.source_id,
  l.*, --  map legend info
  tile_layers.tile_geom(z.geom, :envelope) AS geom
FROM maps.polygons p
JOIN maps.sources s
  ON p.source_id = s.source_id
LEFT JOIN maps.map_legend ml
  ON p.map_id = ml.map_id
LEFT JOIN tile_layers.map_legend_info AS l
  ON l.legend_id = ml.legend_id
WHERE s.slug = :slug
  AND ST_Intersects(geom, ST_Transform(:envelope, 4326))
