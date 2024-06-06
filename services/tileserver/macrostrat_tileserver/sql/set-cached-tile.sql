INSERT INTO tile_cache.tile (x, y, z, params, profile, tile)
VALUES (
  :x,
  :y,
  :z,
  :params,
  :profile,
  :tile
)
ON CONFLICT (x, y, z, params, profile)
DO UPDATE
SET 
  tile = EXCLUDED.tile,
  created = now();