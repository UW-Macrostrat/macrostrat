-- Casts keep each parameter's type fixed where it is compared as well as stored.
INSERT INTO tile_cache.tile (x, y, z, args_hash, profile, generation, tile, sources)
SELECT
  CAST(:x AS integer),
  CAST(:y AS integer),
  CAST(:z AS integer),
  CAST(:params AS integer),
  CAST(:profile AS integer),
  CASE
    WHEN CAST(:z AS integer) <= s.pin_max_zoom
      OR CAST(:render_ms AS integer) >= s.pin_min_render_ms THEN 0
    ELSE s.current_generation
  END,
  CAST(:tile AS bytea),
  CAST(:sources AS integer[])
FROM tile_cache.state s
ON CONFLICT (x, y, z, profile, args_hash, generation)
DO UPDATE
SET
  tile = EXCLUDED.tile,
  sources = EXCLUDED.sources,
  created = now();
