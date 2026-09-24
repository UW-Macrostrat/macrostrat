/** A face per member of a registered compilation, alongside the faces of the
  maps it resolves to.

  British Columbia occupies 5,113 faces in `medium`, held apart only by the
  bedrock / surficial distinction -- internal detail nobody outside `bc-surface`
  means to see. As one unit it is a single face with 19 parts.

  These are ordinary `map_face` rows built the ordinary way: an element array of
  the primitive faces the unit covers, handed to `createTopoGeom`, with `geometry`
  read back off the topogeometry. Nothing marks them apart but their `map_id`,
  which names a compilation rather than a map -- and that is enough to choose
  between levels, since `has_content(map_id)` tells them apart.

  Both levels coexist deliberately. Polygon selection keeps resolving to where the
  polygons actually are, through the constituent faces, exactly as before; footprint
  and usage-region displays ask for the unit instead. Same graph, different
  traversal.
*/

/* Release the previous topogeometries first: deleting a `map_face` row does not
   cascade to its `relation` elements, so without this each run orphans them --
   about 29,600 rows a time. */
SELECT topology.clearTopoGeom(mf.topo)
FROM map_bounds_topology.map_face mf
WHERE mf.map_id IS NOT NULL
  AND mf.topo IS NOT NULL
  AND NOT map_bounds.has_content(mf.map_id);

DELETE FROM map_bounds_topology.map_face mf
WHERE mf.map_id IS NOT NULL
  AND NOT map_bounds.has_content(mf.map_id);

INSERT INTO map_bounds_topology.map_face (map_layer, map_id, topo, geometry)
SELECT
  u.map_layer,
  u.member_id,
  t.topo,
  ST_SetSRID(ST_Multi(t.topo::geometry), 4326)
FROM (
  SELECT
    mp.map_layer,
    mp.member_id,
    array_agg(DISTINCT ARRAY[r.element_id, 3]) AS elements
  FROM map_bounds.map_priority mp
  JOIN map_bounds_topology.map_face f
    ON f.map_layer = mp.map_layer
   AND f.map_id = mp.map_id
  JOIN map_bounds_topology.relation r
    ON r.layer_id = (f.topo).layer_id
   AND r.topogeo_id = (f.topo).id
   AND r.element_type = 3
  -- Only where a compilation is involved. A map directly in the compilation is
  -- its own member, and its existing faces already are the answer.
  WHERE mp.member_id IS DISTINCT FROM mp.map_id
  GROUP BY mp.map_layer, mp.member_id
) u
CROSS JOIN LATERAL (
  SELECT topology.createTopoGeom(
    'map_bounds_topology',
    3,
    map_bounds_topology.__map_face_layer_id(),
    u.elements
  ) AS topo
) t;
