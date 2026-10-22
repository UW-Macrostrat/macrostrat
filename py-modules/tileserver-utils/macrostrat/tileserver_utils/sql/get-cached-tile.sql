-- The pinned copy wins; otherwise the copy from the most recent generation.
WITH found AS (
  SELECT
    t.tile,
    t.sources,
    t.generation,
    mod(s.current_generation - t.generation + s.generations, s.generations) AS behind,
    s.promote_distance
  FROM tile_cache.tile t
  CROSS JOIN tile_cache.state s
  WHERE t.x = :x
    AND t.y = :y
    AND t.z = :z
    AND t.profile = :layer
    AND t.args_hash = :params
)
SELECT
  tile,
  sources,
  generation,
  generation <> 0 AND behind >= promote_distance AS should_promote
FROM found
ORDER BY generation = 0 DESC, behind
LIMIT 1
