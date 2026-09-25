/* Everything covering a point, at every level of the compilation hierarchy.

   `map_priority` is deliberately *not* the source here: it holds only the
   resolved maps of each registered compilation, which is the wrong shape twice
   over. A virtual compilation (mid-atlantic) never gets a row of its own even
   though the map and face tiles are drawn at that level, and a materialized one
   (bc-surface) swallows its members entirely, since materialization is what
   terminates the descent.

   So this walks `compilation_member` itself, all the way down, and emits a row
   per source -- compilation and member alike -- with flags describing each.
   Nothing is chosen server-side; a client filters or groups the tree as it needs.

   The walk is pruned by bounds: a compilation's `map_area` geometry covers its
   members (exactly for a regional compilation, as an envelope for a global one),
   so a source that misses the point cannot have a member that hits it, and the
   whole covering set can be resolved up front in one spatial scan.
*/
WITH RECURSIVE loc AS (
  SELECT ST_SetSRID(ST_MakePoint(:lng, :lat), 4326) AS geometry
),
covering AS MATERIALIZED (
  /* Every map whose footprint covers the point, resolved once. Folding this into
     the recursion instead re-scans `map_area` on every iteration. */
  SELECT ma.source_id
  FROM map_bounds.map_area ma, loc
  WHERE ST_Intersects(ma.geometry, loc.geometry)
),
covering_face AS MATERIALIZED (
  /* Likewise for solved faces: one spatial scan, joined back by map. Left as a
     correlated join the planner re-runs it once per output row. */
  SELECT mf.id, mf.map_id, mf.map_layer
  FROM map_bounds_topology.map_face mf, loc
  WHERE ST_Intersects(mf.geometry, loc.geometry)
),
nodes AS (
  /* Roots are the registered compilations (those with faces) -- structural
     containers, never emitted. */
  SELECT
    ml.id AS map_layer,
    ml.source_id AS source_id,
    ARRAY[]::integer[] AS path,
    NULL::integer AS parent_id,
    NULL::integer AS member_id,
    0 AS depth
  FROM map_bounds.map_layer ml
  WHERE ml.source_id IN (SELECT source_id FROM covering)
    AND ::layer_filter
  UNION ALL
  SELECT
    n.map_layer,
    cm.member_id,
    n.path || coalesce(cm.priority, 0),
    n.source_id,
    /* The member of the registered compilation this row belongs to, skipping
       intermediate registered compilations (the scale layers). This is the level
       the `maps` and `faces` tiles draw by default, so a row whose `member_id` is
       its own `source_id` is what matches a clicked feature. */
    coalesce(
      n.member_id,
      CASE WHEN map_bounds.has_faces(cm.member_id) THEN NULL
           ELSE cm.member_id END
    ),
    n.depth + 1
  FROM nodes n
  JOIN map_bounds.compilation_member cm
    ON cm.compilation_id = n.source_id
  WHERE cm.member_id IN (SELECT source_id FROM covering)
),
/* A map can be reachable under one layer by more than one route -- directly and
   again through a compilation, the state a half-migrated compilation is in. The
   winning route is the one that would win anyway. */
resolved AS (
  SELECT DISTINCT ON (map_layer, source_id) *
  FROM nodes
  WHERE depth > 0
    AND NOT map_bounds.has_faces(source_id)
  ORDER BY map_layer, source_id, path DESC
)
SELECT
    n.source_id,
    s.slug,
    s.name,
    s.scale,
    ml.slug AS map_layer,
    ml.id AS map_layer_id,
    ml.name AS layer_name,
    array_to_string(n.path, '.') AS priority,
    n.path AS priority_path,
    n.depth,
    /* The compilation this row was reached through. May be a registered
       compilation, in which case it has no row of its own. */
    n.parent_id,
    k.is_compilation,
    /* Holds polygons of its own -- an ordinary map, a materialized compilation. */
    k.is_materialized,
    /* Those polygons are a cache cut from its members'. False for SGMC, whose
       polygons are originals and whose members are provenance. */
    k.is_derived,
    /* The member of the registered compilation this row belongs to; equal to
       `source_id` for the row that matches a clicked feature. */
    n.member_id,
    v.slug AS member_slug,
    v.name AS member_name,
    mf.id AS map_face_id
FROM resolved n
CROSS JOIN LATERAL (
  SELECT
    map_bounds.is_compilation(n.source_id) AS is_compilation,
    map_bounds.is_materialized(n.source_id) AS is_materialized,
    map_bounds.is_derived(n.source_id) AS is_derived
) k
JOIN map_bounds.map_layer ml ON ml.id = n.map_layer
JOIN maps.sources s ON s.source_id = n.source_id
LEFT JOIN maps.sources v ON v.source_id = n.member_id
LEFT JOIN covering_face mf
  ON mf.map_id = n.source_id
  AND mf.map_layer = n.map_layer
ORDER BY ml.id, n.path DESC;
