/* Every compilation in the system, as the nodes of the compilation graph.

   "Is a compilation" means *has members* -- there is no kind flag -- so the node
   set is the distinct left-hand side of `compilation_member`. Served layers are
   included: a layer is a compilation that happens to be served as a tile layer,
   and leaving them out would hide the roots of the graph.

   Only compilations are returned. The ordinary maps at the bottom are reached by
   expanding a node (`GET /compilations/{ident}`), which keeps this response the
   size of the graph rather than the size of the map catalog.

   `parent_ids` is what lets a client assemble the tree without a second request:
   a root is a node no other node claims. A compilation can have more than one
   parent -- `medium` sits under both `carto-medium` and `carto-large` -- so the
   graph is a DAG, not a tree, and the client renders it as a tree by repeating
   shared nodes.

   Given `:lng`/`:lat`, only the compilations covering that point are returned.
   The set stays closed upward -- a compilation's leaves are a superset of any
   member's -- so roots remain roots and the tree still assembles.
*/
WITH loc AS (
  SELECT CASE
    WHEN CAST(:lng AS float) IS NULL OR CAST(:lat AS float) IS NULL THEN NULL
    ELSE ST_SetSRID(
      ST_MakePoint(CAST(:lng AS float), CAST(:lat AS float)), 4326)
  END AS geometry
),
/* Resolved once: folded into the node scan the planner re-runs the GiST scan per
   row. Testing `map_area` directly is exact *for leaves*, which is all this is
   used for -- a compilation's own `map_area.geometry` is only an envelope. */
covering AS MATERIALIZED (
  SELECT ma.source_id
  FROM map_bounds.map_area ma, loc
  WHERE loc.geometry IS NOT NULL
    AND ST_Intersects(ma.geometry, loc.geometry)
),
nodes AS (
  SELECT DISTINCT compilation_id AS source_id
  FROM map_bounds.compilation_member
)
SELECT
  s.source_id,
  s.slug,
  /* A served layer carries its name on `map_layer`; its `maps.sources` row is a
     bridge minted by the schema and has none. */
  coalesce(s.name, ml.name) AS name,
  s.scale,
  ml.id IS NOT NULL AS is_served_layer,
  ml.id AS map_layer,
  ml.min_zoom,
  ml.max_zoom,
  true AS is_compilation,
  map_bounds.holds_polygons(s.source_id) AS holds_polygons,
  map_bounds.holds_polygons(s.source_id) AS is_materialized,
  map_bounds.is_mosaic_member(s.source_id) AS is_mosaic_member,
  cs.n_members,
  /* What the compilation actually resolves to, descending through member
     compilations to the maps at the bottom -- so `carto-large` reads 2 and 384. */
  lv.n_sources,
  cs.assembly_mode,
  cs.content,
  cs.state,
  ma.area_km::float AS area_km,
  coalesce(par.parent_ids, '{}'::integer[]) AS parent_ids
FROM nodes n
JOIN maps.sources s USING (source_id)
JOIN map_bounds.compilation_sync cs USING (source_id)
LEFT JOIN map_bounds.map_layer ml ON ml.source_id = s.source_id
LEFT JOIN map_bounds.map_area ma ON ma.source_id = s.source_id
CROSS JOIN LATERAL (
  SELECT count(DISTINCT source_id) AS n_sources
  FROM map_bounds.compilation_leaves(s.source_id, true)
) lv
LEFT JOIN LATERAL (
  SELECT array_agg(cm.compilation_id ORDER BY cm.compilation_id) AS parent_ids
  FROM map_bounds.compilation_member cm
  WHERE cm.member_id = s.source_id
) par ON true
WHERE (SELECT geometry FROM loc) IS NULL
  /* A compilation covers the point when one of the maps it resolves to does.
     Its own footprint is an envelope, so asking it directly would answer yes
     over the whole bounding box. */
  OR EXISTS (
    SELECT 1
    FROM map_bounds.compilation_leaves(s.source_id, true) l
    WHERE l.source_id IN (SELECT source_id FROM covering)
  )
ORDER BY s.slug;
