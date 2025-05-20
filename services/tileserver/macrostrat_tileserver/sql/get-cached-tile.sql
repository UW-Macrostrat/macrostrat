WITH cached_tile AS (
  UPDATE tile_cache.tile
    SET last_used = now()
  WHERE x = :x
    AND y = :y
    AND z = :z
    AND profile = :layer
    AND args_hash = :params
  RETURNING *
)
SELECT
  t.tile,
  t.args_hash,
  p.id profile,
  p.content_type
FROM cached_tile t
JOIN tile_cache.profile p
  ON t.profile = p.id