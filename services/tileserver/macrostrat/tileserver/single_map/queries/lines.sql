SELECT
  l.line_id,
  l.source_id,
  coalesce(l.descrip, '') AS descrip,
  coalesce(l.name, '') AS name,
  coalesce(l.direction, '') AS direction,
  coalesce(l.type, '') AS "type",
  s.lines_oriented oriented,
  tile_layers.tile_geom(l.geom, :envelope) AS geom
FROM maps.lines l
JOIN maps.sources s ON l.source_id = s.source_id
WHERE s.slug = :slug
  AND ST_Intersects(geom, ST_Transform(:envelope, 4326))
