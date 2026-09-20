/** Flatten the composition DAG into the paths identity resolution orders by.

  One recursion, because there is one edge table. A served layer is just a
  compilation with a `map_layer` row, so the walk starts at each of those and
  descends `compilation_member` until it reaches something with content. A
  *virtual* compilation is descended through, so a face resolves to whoever
  actually has the geometry; anything with content is a leaf -- a map, a
  materialized compilation, or a mosaic member placed here directly, which holds
  no polygons but stands for its parent's inside its footprint (`has_content`).
  Stopping at content is also what keeps a mosaic's members out of the walk: the
  mosaic itself is the leaf.

  Every row here is derived -- the table is rebuilt outright.
*/

DELETE FROM map_bounds.map_priority;

WITH RECURSIVE paths AS (
  SELECT
    ml.id AS map_layer,
    ml.source_id,
    ARRAY[]::integer[] AS path,
    NULL::integer AS via
  FROM map_bounds.map_layer ml
  WHERE ml.source_id IS NOT NULL
  UNION ALL
  SELECT
    p.map_layer,
    cm.member_id,
    p.path || coalesce(cm.priority, 0),
    -- The unit a map is presented as: the first member on the way down that is
    -- not a served layer. Layers are structural containers -- nobody means to
    -- see `medium` -- so the meaningful ancestor is one level further.
    coalesce(
      p.via,
      CASE WHEN map_bounds.is_served_layer(cm.member_id) THEN NULL
           ELSE cm.member_id END
    )
  FROM paths p
  JOIN map_bounds.compilation_member cm
    ON cm.compilation_id = p.source_id
  WHERE NOT map_bounds.has_content(p.source_id)
),
/** A map can be reachable under one layer by more than one route -- directly and
  again through a compilation, which is the state a half-migrated compilation is
  in. The winning route is the one that would win anyway. */
leaves AS (
  SELECT DISTINCT ON (map_layer, source_id) map_layer, source_id, path, via
  FROM paths
  WHERE map_bounds.has_content(source_id)
  ORDER BY map_layer, source_id, path DESC
)
INSERT INTO map_bounds.map_priority (map_layer, source_id, priority_path, via)
SELECT map_layer, source_id, path, coalesce(via, source_id)
FROM leaves;


/** Project the layer-to-layer edges back into the submodule's own table.

  `map_layer_composition` is the library's; Macrostrat's authored edges all live
  in `compilation_member`, so this keeps the library's view of composition in
  step without giving it a second source of truth. It is what `constraining_layers`
  reads when deciding which boundaries constrain a dissolve, and what
  `dirty_layers_for` reads when deciding which composites a change invalidates.
*/
DELETE FROM map_bounds.map_layer_composition;

INSERT INTO map_bounds.map_layer_composition (parent_id, member_id, priority)
SELECT parent.id, member.id, coalesce(cm.priority, 0)
FROM map_bounds.compilation_member cm
JOIN map_bounds.map_layer parent ON parent.source_id = cm.compilation_id
JOIN map_bounds.map_layer member ON member.source_id = cm.member_id;


/* Placed here, not in `set-map-priority`, because it reads two tables this file
   rebuilds: `map_priority`, for where a map participates, and (through
   `is_composite_layer`) `map_layer_composition`. Run a statement earlier and it
   sees the previous sync's answer, or on a fresh database no answer at all. */
/** Register each map's footprint in the base layer it actually participates in.

  `map_area.map_layer` is what `__edge_relation` keys on, so it decides where a
  map's footprint acts as a *barrier* during the dissolve. That is a different
  question from where the map ranks, which is `map_priority`'s job, and the two
  agreed only for as long as layer membership was a function of scale.

  Compilations broke that. A member participates in whatever layer its
  compilation is served at, whatever its own scale: `ngs-oklahoma` is 1:250,000
  and therefore `large`, but it reaches medium, carto-medium and carto-large
  through `ngs-bedrock` and has no placement in `large` at all. Keyed on scale it
  registered its boundary in `large` -- a layer it is not in -- and was invisible
  as a barrier in all three layers where it is. 23 maps were in that state.

  The cost is not a misranking, it is a hole. `joinable_face_edges` crosses any
  edge that is not a barrier *regardless of identity* -- identity only rescues an
  edge that is one -- so the walk runs straight through an unregistered footprint
  and merges the maps on either side. One face ended up holding 35,645 primitive
  faces spanning 42 different maps' territory, taking its name from whichever map
  the merged geometry's `ST_PointOnSurface` happened to fall in.

  The *base* layer is the right choice and keeps this a single column: every
  composite layer containing a map lists its base layer in `constraining_layers`,
  so one registration covers all of them. True of every participation pattern in
  the corpus -- {4,7}->4, {3,6,7}->3, {2,5,6}->2, {1,5}->1.

  `is_composite_layer` is the test, not the lowest id. Production ids happen to
  run base-first (1-4 base, 5-7 carto) so `min()` gives the same answer there and
  the wrong one wherever a composite layer was created first -- which the
  submodule's own fixtures do, so `test_composite_layers` catches it.

  Scale is deliberately not the key. It is the `maps.polygons` partition key, so
  moving a map between layers by editing it would move its polygons between
  partitions, and it is a real property of the work: `ngs-connecticut` is
  1:125,000 whatever layer happens to serve it.

  The update does double duty, so its guard has two arms. `update_line_edge_relation`
  fires on *any* update of a `map_area` holding a topogeometry and rebuilds that
  map's `__edge_relation` rows, so this statement is also what populates the
  barrier registry on a database being built from scratch. Without any barriers the
  dissolve merges everything it can reach and a composite layer collapses to a
  single face.

  It used to be unconditional for that reason, which made every run delete and
  re-insert the whole registry: 457 maps, 720,556 rows, about 24 s, on a run where
  no map had moved at all (measured 2026-09-18, where 0 of 469 rows changed layer
  and 0 were missing barrier rows). So the two duties are now stated separately --
  a map whose layer moved, or a map holding a topogeometry with no barrier rows
  yet. A steady-state run touches nothing; a fresh database still populates.

  The trade this makes is deliberate: the unconditional rebuild also repaired
  `__edge_relation` rows that were present but *wrong*, on every run. The second
  arm only catches rows that are missing. `macrostrat topo rebuild` remains the
  repair path, and `validate_edge_relations` the check.

  Scale remains the fallback, for a map with no placement to read. That is not
  only the ~95 ingested maps that are in no layer -- where a stale registration
  can at worst add a barrier, over-fragmenting a dissolve without misattributing
  it, which is what they do today -- but any database whose layers have no
  compilation behind them yet. The submodule's fixtures seed `map_layer` without
  a `source_id`, so there is no placement to read at all there, and without the
  fallback every map loses its layer.
*/
UPDATE map_bounds.map_area ma
SET map_layer = coalesce(base.map_layer, map_bounds.layer_id(s.scale))
FROM maps.sources s
LEFT JOIN (
  SELECT source_id, min(map_layer) AS map_layer
  FROM map_bounds.map_priority
  WHERE NOT map_bounds.is_composite_layer(map_layer)
  GROUP BY source_id
) base ON base.source_id = s.source_id
WHERE ma.source_id = s.source_id
  AND (
    -- The map moved between layers.
    ma.map_layer IS DISTINCT FROM coalesce(base.map_layer, map_bounds.layer_id(s.scale))
    -- Or it holds a boundary whose barrier rows were never registered, which is
    -- what the trigger on this statement is here to do.
    OR (
      ma.topo IS NOT NULL
      AND NOT EXISTS (
        SELECT 1 FROM map_bounds_topology.__edge_relation er WHERE er.line_id = ma.id
      )
    )
  );
