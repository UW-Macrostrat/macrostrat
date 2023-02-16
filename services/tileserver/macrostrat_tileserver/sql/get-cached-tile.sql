WITH cached_tile AS (
  UPDATE tile_cache.tile
    SET last_used = now()
  WHERE x = :x
    AND y = :y
    AND z = :z
    AND profile = :layer
    AND tms = coalesce(:tms, current_setting('tile_utils.default_tms')) 
  RETURNING *
)
SELECT
  t.tile,
  t.layers,
  p.content_type,
  p.name
FROM cached_tile t
JOIN tile_cache.profile p
  ON t.profile = p.name