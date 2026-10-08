INSERT INTO tile_cache.tile (x, y, z, args_hash, profile, tile, sources)
VALUES (
  :x,
  :y,
  :z,
  :params,
  :profile,
  :tile,
  :sources
)
ON CONFLICT (x, y, z, args_hash, profile)
DO UPDATE
SET
  tile = EXCLUDED.tile,
  sources = EXCLUDED.sources,
  created = now();
