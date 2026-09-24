/* Everything covering a point, at every level of the compilation hierarchy.

   `map_priority` is deliberately *not* the source here: it holds only the leaves
   of each layer's descent, which is the wrong shape twice over. A virtual
   compilation (mid-atlantic) never gets a row of its own even though the map and
   face tiles are drawn at that level, and a materialized one (bc-surface)
   swallows its constituents entirely, since materialization is what terminates
   the descent.

   So this walks `compilation_member` itself, all the way down, and emits a row
   per node -- compilation and constituent alike -- with flags describing each.
   Nothing is chosen server-side; a client filters or groups the tree as it needs.

   The walk is pruned by footprint: a compilation's `map_area` geometry covers
   its members (exactly for a region compilation, as an envelope for a served
   layer), so a node that misses the point cannot have a descendant that hits it,
   and the whole covering set can be resolved up front in one spatial scan.
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
  /* Roots are the served layers -- structural containers, never emitted. */
  SELECT
    ml.id AS map_layer,
    ml.source_id AS source_id,
    ARRAY[]::integer[] AS path,
    NULL::integer AS parent_id,
    NULL::integer AS via,
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
    /* The unit a map is presented as: the first member on the way down that is
       not a served layer. This is the level the `maps` and `faces` tiles are
       drawn at by default, so `is_unit` is what matches a clicked feature. */
    coalesce(
      n.via,
      CASE WHEN map_bounds.is_served_layer(cm.member_id) THEN NULL
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
    AND NOT map_bounds.is_served_layer(source_id)
  ORDER BY map_layer, source_id, path DESC
)
SELECT
    n.source_id,
    s.slug,
    s.name,
    s.scale,
    ml.slug AS map_layer,
    ml.name AS layer_name,
    array_to_string(n.path, '.') AS priority,
    n.path AS priority_path,
    n.depth,
    /* The compilation this row was reached through. May be a served layer, in
       which case it has no row of its own. */
    n.parent_id,
    k.is_compilation,
    /* `holds_polygons`: the row owns polygons -- true for an ordinary map, and
       for a compilation once materialized or, as SGMC, ingested holding them. */
    k.holds_polygons,
    /* A compilation whose polygons are a cache cut from its members'. False for
       an ingested compilation such as SGMC, whose members are provenance. */
    k.is_materialized,
    n.source_id IS DISTINCT FROM n.via AS is_constituent,
    n.source_id = n.via AS is_unit,
    n.via AS unit_id,
    v.slug AS unit,
    v.name AS unit_name,
    map_bounds.holds_polygons(n.via) AS unit_is_materialized,
    mf.id AS map_face_id
FROM resolved n
CROSS JOIN LATERAL (
  SELECT
    EXISTS (
      SELECT 1 FROM map_bounds.compilation_member cm
      WHERE cm.compilation_id = n.source_id
    ) AS is_compilation,
    map_bounds.holds_polygons(n.source_id) AS holds_polygons,
    map_bounds.is_materialized(n.source_id) AS is_materialized
) k
JOIN map_bounds.map_layer ml ON ml.id = n.map_layer
JOIN maps.sources s ON s.source_id = n.source_id
LEFT JOIN maps.sources v ON v.source_id = n.via
LEFT JOIN covering_face mf
  ON mf.map_id = n.source_id
  AND mf.map_layer = n.map_layer
ORDER BY ml.id, n.path DESC;
