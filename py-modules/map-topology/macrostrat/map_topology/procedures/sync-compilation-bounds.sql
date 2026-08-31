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
   the face-based assembly this approach replaced. */
SELECT topology.clearTopoGeom(a.topo)
FROM map_bounds.map_area a
WHERE a.topo IS NOT NULL
  AND NOT map_bounds.holds_polygons(a.source_id)
  AND EXISTS (
    SELECT 1 FROM map_bounds.compilation_member cm
    WHERE cm.compilation_id = a.source_id
  );

UPDATE map_bounds.map_area ma
SET topo = NULL
WHERE ma.topo IS NOT NULL
  AND NOT map_bounds.holds_polygons(ma.source_id)
  AND EXISTS (
    SELECT 1 FROM map_bounds.compilation_member cm
    WHERE cm.compilation_id = ma.source_id
  );

/* An empty placeholder satisfies the NOT NULL; the real extent arrives below. */
INSERT INTO map_bounds.map_area (id, geometry, map_layer)
SELECT DISTINCT
  cm.compilation_id,
  ST_GeomFromText('MULTIPOLYGON EMPTY', 4326),
  map_bounds.layer_id(s.scale)
FROM map_bounds.compilation_member cm
JOIN maps.sources s ON s.source_id = cm.compilation_id
WHERE s.status_code = 'active'
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

/* `geometry` is deliberately *not* materialised for a compilation.

   `composite_topo` already holds the exact footprint, as references; resolving it
   costs ~40s and 19MB for a global layer, and `sync_source_rgeom` would mirror
   every byte into `maps.sources.rgeom` -- 73MB across the seven layers, into the
   table whose size already makes client listings painful. What the geometry
   bought was a coarse spatial filter, and the constituents' own footprints serve
   that better: `identity_for_area` already resolves through them.

   The envelope is kept instead: it satisfies the NOT NULL, costs milliseconds,
   and answers "roughly where is this" for listings. Anything needing the precise
   footprint resolves `composite_topo::geometry`. `area_km` stays NULL for the
   same reason -- an envelope's area would be a wrong answer rather than no
   answer. */
UPDATE map_bounds.map_area ma
SET geometry = ST_Multi(box.envelope),
    area_km = NULL
FROM map_bounds.compilation_assembly ca
CROSS JOIN LATERAL (
  SELECT ST_Envelope(ST_Collect(ST_Envelope(m.geometry))) AS envelope
  FROM map_bounds.compilation_member cm
  JOIN map_bounds.map_area m ON m.source_id = cm.member_id
  WHERE cm.compilation_id = ca.source_id
    -- An empty member envelopes to an empty GeometryCollection, which will not
    -- cast into a MultiPolygon column.
    AND NOT ST_IsEmpty(m.geometry)
) box
WHERE ca.source_id = ma.source_id
  AND ca.is_stale
  AND box.envelope IS NOT NULL;

/* Record what was assembled, so the next run can skip it. Last, so a failure
   part-way leaves the compilation stale rather than falsely current. */
INSERT INTO map_bounds.compilation (source_id, assembly_hash)
SELECT ca.source_id, ca.current_hash
FROM map_bounds.compilation_assembly ca
WHERE ca.is_stale
ON CONFLICT (source_id) DO UPDATE SET assembly_hash = EXCLUDED.assembly_hash;
