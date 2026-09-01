/** Flatten the composition DAG into the paths identity resolution orders by.

  One recursion, because there is one edge table. A served layer is just a
  compilation with a `map_layer` row, so the walk starts at each of those and
  descends `compilation_member` until it reaches a map that holds its own
  polygons. A *virtual* compilation is descended through, so a face resolves to
  whoever actually has the geometry; a *materialized* one is a leaf, which is
  also what keeps a compilation's constituents out of the topology without a
  filter of their own.

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
  WHERE NOT map_bounds.holds_polygons(p.source_id)
),
/** A map can be reachable under one layer by more than one route -- directly and
  again through a compilation, which is the state a half-migrated compilation is
  in. The winning route is the one that would win anyway. */
leaves AS (
  SELECT DISTINCT ON (map_layer, source_id) map_layer, source_id, path, via
  FROM paths
  WHERE map_bounds.holds_polygons(source_id)
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
