/* Where a map sits among the compilations: whether carto draws it, through
   which base layers, and the other compilations it belongs to.

   The carto stacks' own nodes -- multiscale compilations, composite layers and
   base layers, as in `neighbors.sql` -- are reported as `carto_layers` rather
   than as compilations: they are how carto is built, not products a reader
   would look for. */
WITH RECURSIVE stack AS (
  SELECT c.source_id, s.slug AS root, 0 AS depth
  FROM map_bounds.compilation c
  JOIN maps.sources s ON s.source_id = c.source_id
  WHERE c.assembly_mode = 'multiscale'
  UNION
  SELECT cm.member_id, stack.root, stack.depth + 1
  FROM map_bounds.compilation_member cm
  JOIN stack ON cm.compilation_id = stack.source_id
  WHERE stack.depth < 2 AND map_bounds.is_compilation(cm.member_id)
),
up AS (
  SELECT cm.compilation_id
  FROM map_bounds.compilation_member cm
  WHERE cm.member_id = :source_id
  UNION
  SELECT cm.compilation_id
  FROM map_bounds.compilation_member cm
  JOIN up ON cm.member_id = up.compilation_id
)
SELECT
  EXISTS (
    SELECT 1 FROM up JOIN maps.sources c ON c.source_id = up.compilation_id
    WHERE c.slug = 'carto'
  ) AS in_carto,
  coalesce((
    SELECT array_agg(DISTINCT c.slug ORDER BY c.slug)
    FROM up
    JOIN stack st ON st.source_id = up.compilation_id
    JOIN maps.sources c ON c.source_id = up.compilation_id
    WHERE st.root = 'carto' AND st.depth = 2
  ), '{}'::text[]) AS carto_layers,
  coalesce((
    SELECT json_agg(json_build_object(
      'source_id', c.source_id, 'slug', c.slug, 'name', c.name
    ) ORDER BY c.name, c.slug)
    FROM up
    JOIN maps.sources c ON c.source_id = up.compilation_id
    WHERE up.compilation_id NOT IN (SELECT source_id FROM stack)
  ), '[]'::json) AS compilations;
