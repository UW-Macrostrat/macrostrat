/** For a while, plate rotations were cached by plate polygons
instead of by plate. This script deduplicates the cache and adds constraints
to the underlying rotation cache table. */
DELETE FROM corelle.rotation_cache rc
WHERE rc.id IN (
  SELECT id
  FROM (
    SELECT id,
      row_number() OVER (PARTITION BY model_id, plate_id, t_step ORDER BY id) AS r
    FROM corelle.rotation_cache
  ) AS sub
  WHERE r > 1
);

ALTER TABLE corelle.rotation_cache ADD CONSTRAINT rotation_cache_unique UNIQUE (model_id, plate_id, t_step);

DELETE FROM tile_cache.tile
WHERE profile = (
  SELECT id FROM tile_cache.profile WHERE name = 'carto-slim-rotated'
);