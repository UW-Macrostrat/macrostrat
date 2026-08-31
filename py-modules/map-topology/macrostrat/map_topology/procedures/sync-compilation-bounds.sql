/** Assemble each compilation's boundary from its members', in topology space.

  A compilation has no features of its own, but its members' boundaries are
  already in the topology. Its boundary is therefore the union of their face
  sets -- an array of element ids handed to `createTopoGeom`, exactly as
  `create-source-topogeometry` does for an ordinary map's own parts. No geometry
  is unioned and no edge is noded, so the expensive half of the topology never
  runs for a compilation.

  Three statements rather than one because the `__edge_relation` trigger fires on
  the topogeometry and its foreign key needs the `map_area` row to exist first --
  the same insert-then-assign order every other map follows. `geometry` is filled
  from the topogeometry afterwards, so it can never drift from the faces.

  Members are allowed to overlap, so each face is claimed once.
*/

/* Release the previous assembly's elements. `createTopoGeom` mints a new
   topogeometry; without this the old one's `relation` rows would be orphaned. */
SELECT topology.clearTopoGeom(a.topo)
FROM map_bounds.map_area a
WHERE a.topo IS NOT NULL
  AND EXISTS (
    SELECT 1 FROM map_bounds.map_composition mc
    WHERE mc.compilation_id = a.source_id
  );

/* An empty placeholder satisfies the NOT NULL; the real extent arrives below,
   read off the assembled topogeometry rather than unioned from scratch. */
INSERT INTO map_bounds.map_area (id, geometry, map_layer)
SELECT DISTINCT
  mc.compilation_id,
  ST_GeomFromText('MULTIPOLYGON EMPTY', 4326),
  map_bounds.layer_id(s.scale)
FROM map_bounds.map_composition mc
JOIN maps.sources s ON s.source_id = mc.compilation_id
WHERE s.status_code = 'active'
ON CONFLICT (id) DO NOTHING;

UPDATE map_bounds.map_area ma
SET topo = topology.createTopoGeom(
      'map_bounds_topology',
      3,
      (
        SELECT layer_id FROM topology.layer
        WHERE schema_name = 'map_bounds'
          AND table_name = 'map_area'
          AND feature_column = 'topo'
      ),
      (
        SELECT array_agg(ARRAY[face_id, 3])
        FROM (
          SELECT r.element_id AS face_id
          FROM map_bounds.map_composition mc
          JOIN map_bounds.map_area a
            ON a.source_id = mc.member_id
           AND a.topo IS NOT NULL
          JOIN map_bounds_topology.relation r
            ON r.layer_id = (a.topo).layer_id
           AND r.topogeo_id = (a.topo).id
           AND r.element_type = 3
          WHERE mc.compilation_id = ma.source_id
          GROUP BY r.element_id
        ) faces
      )
    )
WHERE EXISTS (
  SELECT 1
  FROM map_bounds.map_composition mc
  JOIN map_bounds.map_area a
    ON a.source_id = mc.member_id
   AND a.topo IS NOT NULL
  WHERE mc.compilation_id = ma.source_id
);

UPDATE map_bounds.map_area ma
SET geometry = ST_Multi(ma.topo::geometry),
    area_km = ST_Area(
      ST_Segmentize(ST_Multi(ma.topo::geometry), 90)::geography
    ) / 1e6
WHERE ma.topo IS NOT NULL
  AND EXISTS (
    SELECT 1 FROM map_bounds.map_composition mc
    WHERE mc.compilation_id = ma.source_id
  );
