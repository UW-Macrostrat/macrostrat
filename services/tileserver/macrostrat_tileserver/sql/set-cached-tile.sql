INSERT INTO tile_cache.tile (x, y, z, layers, profile, tile)
VALUES (
  :x,
  :y,
  :z,
  :layers,
  'mars_imagery',
  :tile
)
ON CONFLICT (x,y,z,layers)
DO UPDATE
SET 
  tile = EXCLUDED.tile,
  created = now();