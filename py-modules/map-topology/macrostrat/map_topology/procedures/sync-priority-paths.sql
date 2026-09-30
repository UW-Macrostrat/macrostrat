/** The face register, and the paths identity resolution orders by.

  Four steps, each reading what the one before it wrote:

  1. **Barriers.** Every map's boundary is recorded in the barrier layer.
  2. **Register.** One layer per solved compilation (`is_solved`), keyed by
     source. A layer whose compilation is no longer solved is removed, with its
     faces. Barriers come first because a map's `map_layer` must point at a
     layer that still exists.
  3. **Paths.** Each solved layer's descent, from its compilation down
     `compilation_member` to whatever has content.
  4. **Composition.** Every solved layer composes the barrier layer, which is how
     a map's bounds are a barrier in each layer that solves it.

  Everything here is derived. `map_priority` and `map_layer_composition` are
  rebuilt outright; a layer is kept while its compilation is solved, so its faces
  survive a sync that changes nothing.
*/

/* ---------------------------------------------------------------- barriers */

/** Record every map's boundary in the barrier layer.

  `map_area.map_layer` is what `__edge_relation` keys on: the library records a
  map's boundary edges under that one layer, and a dissolve of a layer treats the
  edges of every layer it composes as barriers. A map missing from the layers
  that solve it is not a misranking but a hole -- `joinable_face_edges` crosses
  any edge that is not a barrier regardless of identity, so the walk runs through
  an unrecorded footprint and merges the maps on either side (one face once held
  35,645 primitives of 42 maps). One shared barrier layer, composed by every
  solved layer, closes that by construction. A layer sees the barriers of maps
  it does not solve too, which costs identity checks and changes nothing: an
  edge with the same identity on both sides is crossed anyway (measured
  2026-09-28: carto's medium and large layers already saw all but 3 of 204,943
  barrier edges under the per-scale layers this replaces).

  The update does double duty, so its guard has two arms.
  `update_line_edge_relation` fires on *any* update of a `map_area` holding a
  topogeometry and rebuilds that map's `__edge_relation` rows, so this statement
  is also what populates the barriers on a database built from scratch. A
  steady-state run touches nothing; `macrostrat topo rebuild` remains the repair
  path for rows that are present but wrong, and `validate_edge_relations` the
  check.
*/
UPDATE map_bounds.map_area ma
SET map_layer = map_bounds.barrier_layer()
WHERE ma.map_layer IS DISTINCT FROM map_bounds.barrier_layer()
  OR (
    ma.topo IS NOT NULL
    AND NOT EXISTS (
      SELECT 1 FROM map_bounds_topology.__edge_relation er WHERE er.line_id = ma.id
    )
  );

/* ---------------------------------------------------------------- register */

DELETE FROM map_bounds.map_layer ml
WHERE ml.source_id IS NOT NULL
  AND NOT map_bounds.is_solved(ml.source_id);

INSERT INTO map_bounds.map_layer (name, source_id, topological, editable)
SELECT coalesce(s.name, s.slug), s.source_id, true, false
FROM maps.sources s
WHERE map_bounds.is_solved(s.source_id)
ON CONFLICT (source_id) DO NOTHING;

/* Topological and not editable: the library's terms for a layer that is solved
   and composed of others. */
UPDATE map_bounds.map_layer ml
SET topological = true, editable = false
WHERE ml.source_id IS NOT NULL
  AND (NOT ml.topological OR ml.editable);

/* ------------------------------------------------------------------- paths */

/** Flatten each solved layer's membership into priority paths.

  The walk starts at the layer's compilation and descends `compilation_member`
  until it reaches something
  with content. A *virtual* compilation is descended through, so a face resolves
  to whoever actually has the geometry; anything with content is a leaf -- a
  map, a materialized compilation, or a mosaic member placed here directly,
  which holds no polygons but stands for its parent's inside its footprint
  (`has_content`). Stopping at content is also what keeps a mosaic's members out
  of the walk: the mosaic itself is the leaf.

  `member_id` is the first *served* source below the compilation: unserved
  compilations exist only to build others -- from `carto-large` British Columbia
  is `bc-surface`, not `medium`.
*/
DELETE FROM map_bounds.map_priority;

WITH RECURSIVE paths AS (
  SELECT
    ml.id AS map_layer,
    ml.source_id,
    ARRAY[]::integer[] AS path,
    NULL::integer AS member_id
  FROM map_bounds.map_layer ml
  WHERE ml.source_id IS NOT NULL
  UNION ALL
  SELECT
    p.map_layer,
    cm.member_id,
    p.path || coalesce(cm.priority, 0),
    coalesce(
      p.member_id,
      CASE WHEN map_bounds.is_served(cm.member_id) THEN cm.member_id END
    )
  FROM paths p
  JOIN map_bounds.compilation_member cm
    ON cm.compilation_id = p.source_id
  WHERE NOT map_bounds.has_content(p.source_id)
),
/** A map can be reachable under one layer by more than one route -- directly and
  again through a compilation, which is the state a half-migrated compilation is
  in. The winning route is the one that would win anyway. */
resolved AS (
  SELECT DISTINCT ON (map_layer, source_id) map_layer, source_id, path, member_id
  FROM paths
  WHERE map_bounds.has_content(source_id)
  ORDER BY map_layer, source_id, path DESC
)
INSERT INTO map_bounds.map_priority (map_layer, map_id, priority_path, member_id)
SELECT map_layer, source_id, path, coalesce(member_id, source_id)
FROM resolved;

/* Faces only belong to a layer with rankings: a layer whose compilation has lost
   its last map to rank is no longer drawn, so its faces go. */
DELETE FROM map_bounds_topology.map_face f
WHERE NOT EXISTS (
  SELECT 1 FROM map_bounds.map_priority mp WHERE mp.map_layer = f.map_layer
);

/* ------------------------------------------------------------- composition */

/** Every solved layer composes the barrier layer.

  `map_layer_composition` is the library's: `constraining_layers` reads it to
  decide which boundaries constrain a dissolve, and `dirty_layers_for` to decide
  which layers a boundary change invalidates -- so a map noded anywhere marks
  every solved layer's faces near it. The library wants a priority per edge;
  nothing here ranks by it.
*/
DELETE FROM map_bounds.map_layer_composition;

INSERT INTO map_bounds.map_layer_composition (parent_id, member_id, priority)
SELECT DISTINCT mp.map_layer, map_bounds.barrier_layer(), 1
FROM map_bounds.map_priority mp;
