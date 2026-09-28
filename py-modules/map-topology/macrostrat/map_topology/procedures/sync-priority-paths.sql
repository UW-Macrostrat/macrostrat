/** The face register, and the paths identity resolution orders by.

  Four steps, each reading what the one before it wrote:

  1. **Register.** One face layer per partition `solved_partitions` names -- a
     served topological compilation, or a band of a served multiscale one. A
     layer whose partition is gone is removed, and its faces with it.
  2. **Barriers.** Every map registers its boundary in the registry for its
     scale.
  3. **Paths.** Each face layer's descent, from its partition's root down
     `compilation_member` to whatever has content.
  4. **Composition.** Each face layer is linked to the registries its maps
     register in, which is how their boundaries become its barriers.

  Everything here is derived. `map_priority` and `map_layer_composition` are
  rebuilt outright; face layers are kept while their partition exists, so their
  faces survive a sync that changes nothing.
*/

/* ---------------------------------------------------------------- register */

DELETE FROM map_bounds.map_layer ml
WHERE ml.source_id IS NOT NULL
  AND NOT EXISTS (
    SELECT 1 FROM map_bounds.solved_partitions() p
    WHERE p.source_id = ml.source_id
      AND p.band IS NOT DISTINCT FROM ml.band
  );

/* Topological and not editable: the library's terms for a layer that is solved
   and composed of others. The slug names the partition -- the compilation's, with
   the band after an `@` for a multiscale one. */
INSERT INTO map_bounds.map_layer (slug, name, source_id, band, topological, editable)
SELECT
  s.slug || coalesce('@' || p.band::text, ''),
  coalesce(s.name, s.slug) || coalesce(' (' || p.band::text || ')', ''),
  p.source_id,
  p.band,
  true,
  false
FROM map_bounds.solved_partitions() p
JOIN maps.sources s ON s.source_id = p.source_id
ON CONFLICT (source_id, band) DO NOTHING;

/* ---------------------------------------------------------------- barriers */

/** Register each map's boundary in the registry for its scale.

  `map_area.map_layer` is what `__edge_relation` keys on, so it decides which
  layers see a map's footprint as a *barrier* during the dissolve: its registry,
  and every face layer composed of that registry (step 4). A map missing from a
  layer it is solved in is not a misranking but a hole -- `joinable_face_edges`
  crosses any edge that is not a barrier regardless of identity, so the walk runs
  through an unregistered footprint and merges the maps on either side (one face
  once held 35,645 primitives of 42 maps). Step 4 closes that by construction:
  every face layer composes the registry of every map it solves, whatever the
  map's scale -- `ngs-oklahoma` is large-scale but solved in medium through
  `ngs-bedrock`, and its registry is composed into `carto@medium`. A registry
  composed into a layer brings the barriers of its other maps too, which costs a
  few more identity checks and changes nothing: an edge with the same identity on
  both sides is crossed anyway.

  The update does double duty, so its guard has two arms.
  `update_line_edge_relation` fires on *any* update of a `map_area` holding a
  topogeometry and rebuilds that map's `__edge_relation` rows, so this statement
  is also what populates the barriers on a database built from scratch. A
  steady-state run touches nothing; `macrostrat topo rebuild` remains the repair
  path for rows that are present but wrong, and `validate_edge_relations` the
  check.
*/
UPDATE map_bounds.map_area ma
SET map_layer = map_bounds.registry_layer(s.scale)
FROM maps.sources s
WHERE ma.source_id = s.source_id
  AND (
    ma.map_layer IS DISTINCT FROM map_bounds.registry_layer(s.scale)
    OR (
      ma.topo IS NOT NULL
      AND NOT EXISTS (
        SELECT 1 FROM map_bounds_topology.__edge_relation er WHERE er.line_id = ma.id
      )
    )
  );

/* ------------------------------------------------------------------- paths */

/** Flatten each partition's membership into priority paths.

  The walk starts at the partition's root -- the compilation, or the band's member
  -- and descends `compilation_member` until it reaches something with content. A
  *virtual* compilation is descended through, so a face resolves to whoever
  actually has the geometry; anything with content is a leaf -- a map, a
  materialized compilation, or a mosaic member placed here directly, which holds
  no polygons but stands for its parent's inside its footprint (`has_content`).
  Stopping at content is also what keeps a mosaic's members out of the walk: the
  mosaic itself is the leaf.

  `member_id` is the first *served* source below the root: unserved compilations
  exist only to build others -- from `carto` British Columbia is `bc-surface`,
  not `carto-large` or `medium`.
*/
DELETE FROM map_bounds.map_priority;

WITH RECURSIVE paths AS (
  SELECT
    ml.id AS map_layer,
    p.root_id AS source_id,
    ARRAY[]::integer[] AS path,
    NULL::integer AS member_id
  FROM map_bounds.map_layer ml
  JOIN map_bounds.solved_partitions() p
    ON p.source_id = ml.source_id
   AND p.band IS NOT DISTINCT FROM ml.band
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

/* ------------------------------------------------------------- composition */

/** Link each face layer to the registries its maps register in.

  `map_layer_composition` is the library's: `constraining_layers` reads it to
  decide which boundaries constrain a dissolve, and `dirty_layers_for` to decide
  which face layers a change to a registry invalidates. The maps are taken
  through `topology_sources_of`, so a materialized compilation contributes the
  registries of the members its identity is found through. The library wants a
  distinct priority per parent; nothing here ranks by it.
*/
DELETE FROM map_bounds.map_layer_composition;

INSERT INTO map_bounds.map_layer_composition (parent_id, member_id, priority)
SELECT
  x.parent_id,
  x.member_id,
  row_number() OVER (PARTITION BY x.parent_id ORDER BY x.member_id)
FROM (
  SELECT DISTINCT mp.map_layer AS parent_id, ma.map_layer AS member_id
  FROM map_bounds.map_priority mp
  CROSS JOIN LATERAL map_bounds.topology_sources_of(mp.map_id) ts
  JOIN map_bounds.map_area ma ON ma.source_id = ts.source_id
  WHERE ma.map_layer IS NOT NULL
    AND ma.map_layer <> mp.map_layer
) x;
