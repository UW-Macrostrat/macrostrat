-- Copy a tile read from an older generation into the current one, so it outlives that generation.
INSERT INTO tile_cache.tile (x, y, z, args_hash, profile, generation, created, tile, sources)
SELECT t.x, t.y, t.z, t.args_hash, t.profile, s.current_generation, t.created, t.tile, t.sources
FROM tile_cache.tile t
CROSS JOIN tile_cache.state s
WHERE t.x = :x
  AND t.y = :y
  AND t.z = :z
  AND t.profile = :layer
  AND t.args_hash = :params
  AND t.generation = :generation
  AND t.generation NOT IN (0, s.current_generation)
ON CONFLICT (x, y, z, profile, args_hash, generation) DO NOTHING;
