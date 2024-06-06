WITH cached_tile AS (
  UPDATE tile_cache.tile
    SET last_used = now()
  WHERE x = :x
    AND y = :y
    AND z = :z
    AND profile = :layer
    AND params = :params
    AND tms = coalesce(:tms, tile_utils.default_tms())
  RETURNING *
)
SELECT
  t.tile,
  t.layers,
  t.params,
  p.name,
  p.content_type
FROM cached_tile t
JOIN tile_cache.profile p
  ON t.profile = p.name