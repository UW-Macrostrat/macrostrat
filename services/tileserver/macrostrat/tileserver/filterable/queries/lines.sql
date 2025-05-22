WITH mvt_features AS (
  SELECT
    line_id,
    source_id,
    geom
  FROM
    :compilation
  WHERE
    scale::text = :mapsize
    AND ST_Intersects(geom, ST_Transform(:envelope, 4326))
)
SELECT
  z.line_id,
  z.source_id,
  coalesce(l.descrip, '') AS descrip,
  coalesce(l.name, '') AS name,
  coalesce(l.direction, '') AS direction,
  coalesce(l.type, '') AS "type",
  tile_layers.tile_geom(z.geom, :envelope) AS geom,
  s.lines_oriented oriented
FROM mvt_features z
LEFT JOIN maps.lines l
  ON z.line_id = l.line_id
  AND l.scale::text = ANY(:linesize)
LEFT JOIN maps.sources s
  ON z.source_id = s.source_id
WHERE s.status_code = 'active'
