-- See `units.sql`: `map_bounds.lines_of` decides which lines the map shows and
-- prunes the partition. `lines_oriented` is a property of the ingested lines, so
-- it comes from the source that holds them, which for a mosaic member is not the
-- map asked for.
SELECT
  l.line_id,
  l.source_id,
  coalesce(l.descrip, '') AS descrip,
  coalesce(l.name, '') AS name,
  coalesce(l.direction, '') AS direction,
  coalesce(l.type, '') AS "type",
  cs.lines_oriented AS oriented,
  tile_layers.tile_geom(l.geom, :envelope) AS geom
FROM map_bounds.lines_of(
  map_bounds.compilation_id(:slug),
  ST_Transform(:envelope, 4326)
) l
JOIN maps.sources cs ON cs.source_id = l.source_id
