SELECT
  t.tile,
  t.layers,
  p.content_type,
  p.name
FROM tile_cache.tile t
JOIN tile_cache.profile p
  ON t.profile = p.name
WHERE t.x = :x
  AND t.y = :y
  AND t.z = :z
  AND :layer = ANY(t.layers)
  AND t.tms = :tms
  AND p.maxzoom >= :z
  AND coalesce(p.minzoom, 0) < :z