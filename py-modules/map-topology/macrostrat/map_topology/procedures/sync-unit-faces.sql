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

/* What each unit should cover now: the primitive faces of the faces it resolves
   to. Only where a compilation is involved -- a map directly in the compilation
   is its own member, and its existing faces already are the answer.

   No ON COMMIT DROP: statements here are committed individually. */
DROP TABLE IF EXISTS _unit_wanted;
CREATE TEMP TABLE _unit_wanted AS
SELECT
  mp.map_layer,
  mp.member_id,
  array_agg(DISTINCT r.element_id ORDER BY r.element_id) AS faces
FROM map_bounds.map_priority mp
JOIN map_bounds_topology.map_face f
  ON f.map_layer = mp.map_layer
 AND f.map_id = mp.map_id
JOIN map_bounds_topology.relation r
  ON r.layer_id = (f.topo).layer_id
 AND r.topogeo_id = (f.topo).id
 AND r.element_type = 3
WHERE mp.member_id IS DISTINCT FROM mp.map_id
GROUP BY mp.map_layer, mp.member_id;

/* A unit face whose topogeometry already holds exactly those primitives is kept.
   Resolving a unit's geometry is the whole cost of this sync -- six units over
   250,000 primitives took ~100 s -- and on a run that moved no primitive of a unit
   it would rebuild the same face. Noding keeps the comparison honest: splitting a
   primitive adds the new face to every topogeometry that held the old one, so a
   unit whose extent changed no longer matches what it should cover. */
DROP TABLE IF EXISTS _unit_kept;
CREATE TEMP TABLE _unit_kept AS
SELECT DISTINCT ON (mf.map_layer, mf.map_id) mf.id, mf.map_layer, mf.map_id
FROM map_bounds_topology.map_face mf
JOIN _unit_wanted w
  ON w.map_layer = mf.map_layer
 AND w.member_id = mf.map_id
WHERE mf.topo IS NOT NULL
  AND w.faces = ARRAY(
    SELECT r.element_id
    FROM map_bounds_topology.relation r
    WHERE r.layer_id = (mf.topo).layer_id
      AND r.topogeo_id = (mf.topo).id
      AND r.element_type = 3
    ORDER BY r.element_id
  )
ORDER BY mf.map_layer, mf.map_id, mf.id;

/* Release the rest first: deleting a `map_face` row does not cascade to its
   `relation` elements, so without this each rebuild orphans them. */
SELECT topology.clearTopoGeom(mf.topo)
FROM map_bounds_topology.map_face mf
WHERE mf.map_id IS NOT NULL
  AND mf.topo IS NOT NULL
  AND NOT map_bounds.has_content(mf.map_id)
  AND mf.id NOT IN (SELECT id FROM _unit_kept);

DELETE FROM map_bounds_topology.map_face mf
WHERE mf.map_id IS NOT NULL
  AND NOT map_bounds.has_content(mf.map_id)
  AND mf.id NOT IN (SELECT id FROM _unit_kept);

INSERT INTO map_bounds_topology.map_face (map_layer, map_id, topo, geometry)
SELECT
  w.map_layer,
  w.member_id,
  t.topo,
  ST_SetSRID(ST_Multi(t.topo::geometry), 4326)
FROM _unit_wanted w
CROSS JOIN LATERAL (
  SELECT topology.createTopoGeom(
    'map_bounds_topology',
    3,
    map_bounds_topology.__map_face_layer_id(),
    ARRAY(SELECT ARRAY[e, 3] FROM unnest(w.faces) e)
  ) AS topo
) t
WHERE NOT EXISTS (
  SELECT 1 FROM _unit_kept k
  WHERE k.map_layer = w.map_layer AND k.map_id = w.member_id
);

/* Read by the caller for its summary. */
SELECT
  (SELECT count(*) FROM _unit_wanted) AS units,
  (SELECT count(*) FROM _unit_kept) AS kept;
