-- See the note in `units.sql`: `maps.lines` is partitioned by LIST (scale) too,
-- so the scale of the requested source is resolved in a subquery to prune the
-- partitions that cannot contain it.
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
  AND l.scale = (
    SELECT s1.scale::maps.map_scale
    FROM maps.sources s1
    WHERE s1.slug = :slug
      AND s1.scale = ANY (enum_range(NULL::maps.map_scale)::text[])
  )
  AND ST_Intersects(l.geom, ST_Transform(:envelope, 4326))
