/** Assemble each compilation's boundary by referencing its members', in the
  hierarchical `composite_topo` layer.

  A compilation has no features of its own; its boundary is the union of its
  members', and those are already topogeometries. So it *references* them rather
  than re-listing every face they cover -- one element per member instead of tens
  of thousands per compilation.

  References are to *transitive leaf* members, not direct ones: `relationtrigger()`
  requires every element to come from the layer's single `child_id`, so one layer
  holds one level of nesting. Flattening to leaves keeps arbitrary nesting depth
  in a single layer. A *materialized* compilation is skipped -- it holds its own
  polygons, so its boundary comes from them like any other map's.

  `map_bounds.compilation_assembly` decides what to build and what has already
  been built. Only stale compilations are touched, because resolving a
  hierarchical topogeometry to a geometry costs tens of seconds each.
*/

/* Release the previous assembly. `createTopoGeom` mints a new topogeometry, so
   without this the old one's `relation` rows would be orphaned. */
SELECT topology.clearTopoGeom(a.composite_topo)
FROM map_bounds.map_area a
JOIN map_bounds.compilation_assembly ca ON ca.source_id = a.source_id
WHERE a.composite_topo IS NOT NULL
  AND ca.is_stale;

/* A compilation belongs in the composite layer, not the primitive one. Clears
   the face-based assembly this approach replaced.

   Compilations with *ingested* content are exempt, and the exemption is load-bearing:
   their boundary is authored, not assembled, so nothing downstream would rebuild
   what this clears. SGMC would lose its 12,787 primitive faces and the
   conterminous US would lose its identity in `medium` -- silently, because
   `compilation_assembly` inner-joins members on `topo IS NOT NULL` and
   documentary members have none, so the rebuild simply never fires. */
SELECT topology.clearTopoGeom(a.topo)
FROM map_bounds.map_area a
WHERE a.topo IS NOT NULL
  AND NOT map_bounds.is_ingested(a.source_id)
  AND EXISTS (
    SELECT 1 FROM map_bounds.compilation_member cm
    WHERE cm.compilation_id = a.source_id
  );

UPDATE map_bounds.map_area ma
SET topo = NULL
WHERE ma.topo IS NOT NULL
  AND NOT map_bounds.is_ingested(ma.source_id)
  AND EXISTS (
    SELECT 1 FROM map_bounds.compilation_member cm
    WHERE cm.compilation_id = ma.source_id
  );

/* A materialized compilation gets a level-0 topogeometry too: `identity_for_face`
   resolves there, so it cannot own a face without one. Same face set, assembled by
   reference -- never noded. */
UPDATE map_bounds.map_area ma
SET topo = topology.createTopoGeom(
      'map_bounds_topology',
      3,
      map_bounds_topology.boundary_layer_id(),
      ca.face_elements
    )
FROM map_bounds.compilation_assembly ca
WHERE ca.source_id = ma.source_id
  AND map_bounds.holds_polygons(ma.source_id);

/* An empty placeholder satisfies the NOT NULL; the real extent arrives below. */
INSERT INTO map_bounds.map_area (id, geometry, map_layer)
SELECT DISTINCT
  cm.compilation_id,
  ST_GeomFromText('MULTIPOLYGON EMPTY', 4326),
  map_bounds.layer_id(s.scale)
FROM map_bounds.compilation_member cm
JOIN maps.sources s ON s.source_id = cm.compilation_id
WHERE s.status_code = 'active'
  AND NOT map_bounds.is_ingested(cm.compilation_id)
ON CONFLICT (id) DO NOTHING;

UPDATE map_bounds.map_area ma
SET composite_topo = topology.createTopoGeom(
      'map_bounds_topology',
      3,
      (
        SELECT layer_id FROM topology.layer
        WHERE schema_name = 'map_bounds'
          AND table_name = 'map_area'
          AND feature_column = 'composite_topo'
      ),
      ca.elements
    )
FROM map_bounds.compilation_assembly ca
WHERE ca.source_id = ma.source_id
  AND ca.is_stale;

/* A region-scale compilation gets its real boundary; a served layer keeps an
   envelope.

   The two differ by two orders of magnitude, and only in one direction does the
   geometry earn its keep. `bc-surface` resolves to 8,418 points -- fewer than
   either member's *stored* geometry, because the topology's form is noded and
   simplified -- and it is rendered, as a source footprint. `carto-large` resolves
   to 1,048,106 points and 16MB, is global, and is never rendered as a footprint
   at all (`map_layer` is null for a served layer, so the tile query skips it).

   Without this a compilation renders as its bounding rectangle, which for
   `bc-surface` is a box over British Columbia sitting on top of the real maps. */
UPDATE map_bounds.map_area ma
SET geometry = ST_Multi(ma.composite_topo::geometry)
FROM map_bounds.compilation_assembly ca
WHERE ca.source_id = ma.source_id
  AND ca.is_stale
  AND ma.composite_topo IS NOT NULL
  AND NOT map_bounds.is_served_layer(ma.source_id);

UPDATE map_bounds.map_area ma
SET area_km = ST_Area(ST_Segmentize(ma.geometry, 90)::geography) / 1e6
FROM map_bounds.compilation_assembly ca
WHERE ca.source_id = ma.source_id
  AND ca.is_stale
  AND NOT map_bounds.is_served_layer(ma.source_id)
  AND NOT ST_IsEmpty(ma.geometry);

/* A served layer's extent is global and unrendered, so the envelope of its
   members is all it needs -- and all it can afford. `area_km` stays NULL rather
   than reporting an envelope's area as if it were the layer's. */
UPDATE map_bounds.map_area ma
SET geometry = ST_Multi(box.envelope),
    area_km = NULL
FROM map_bounds.compilation_assembly ca
CROSS JOIN LATERAL (
  SELECT ST_Envelope(ST_Collect(ST_Envelope(m.geometry))) AS envelope
  FROM map_bounds.compilation_member cm
  JOIN map_bounds.map_area m ON m.source_id = cm.member_id
  WHERE cm.compilation_id = ca.source_id
    AND NOT ST_IsEmpty(m.geometry)
) box
WHERE ca.source_id = ma.source_id
  AND ca.is_stale
  AND map_bounds.is_served_layer(ma.source_id)
  AND box.envelope IS NOT NULL;

/* Record what was assembled, so the next run can skip it. Last, so a failure
   part-way leaves the compilation stale rather than falsely current. */
INSERT INTO map_bounds.compilation (source_id, assembly_hash)
SELECT ca.source_id, ca.current_hash
FROM map_bounds.compilation_assembly ca
WHERE ca.is_stale
ON CONFLICT (source_id) DO UPDATE SET assembly_hash = EXCLUDED.assembly_hash;
