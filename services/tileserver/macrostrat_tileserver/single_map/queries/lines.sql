SELECT
  l.line_id,
  l.source_id,
  coalesce(l.descrip, '') AS descrip,
  coalesce(l.name, '') AS name,
  coalesce(l.direction, '') AS direction,
  coalesce(l.type, '') AS "type",
  tile_layers.tile_geom(l.geom, :envelope) AS geom
FROM maps.lines l
WHERE l.source_id = :source_id
  AND ST_Intersects(geom, ST_Transform(:envelope, 4326))
