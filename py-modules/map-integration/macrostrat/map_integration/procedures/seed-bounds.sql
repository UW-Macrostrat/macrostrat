/** A map's boundary as the union of its features.

  The features are the map's polygons in `maps`, or its staging table before the
  insert. A position-0 `union` operation records that the boundary is derived
  only from features, which is what lets the next run replace it; the caller
  leaves any other boundary alone. `rgeom` follows by trigger.
*/
WITH u AS (
  SELECT ST_Multi(ST_CollectionExtract(ST_MakeValid(ST_Union(geom)), 3)) AS geometry
  FROM ({features}) f
)
INSERT INTO map_bounds.map_area (id, geometry, area_km, map_layer)
SELECT
  :source_id,
  u.geometry,
  ST_Area(ST_Segmentize(u.geometry, 90)::geography) / 1e6,
  map_bounds.barrier_layer()
FROM u
WHERE u.geometry IS NOT NULL
ON CONFLICT (id) DO UPDATE
SET geometry = EXCLUDED.geometry,
    area_km = EXCLUDED.area_km,
    geometry_hash = NULL
WHERE map_area.geometry IS DISTINCT FROM EXCLUDED.geometry;

-- `bounds build` replays from the opening's cached geometry, so it must agree.
UPDATE map_bounds.boundary_op o
SET geometry = a.geometry
FROM map_bounds.map_area a
WHERE a.id = :source_id
  AND o.source_id = :source_id
  AND o.position = 0
  AND o.operation = 'union';

INSERT INTO map_bounds.boundary_op (source_id, position, operation, geometry, note)
SELECT a.id, 0, 'union', a.geometry, 'Union of the map''s features'
FROM map_bounds.map_area a
WHERE a.id = :source_id
  AND NOT EXISTS (
    SELECT 1 FROM map_bounds.boundary_op o
    WHERE o.source_id = :source_id AND o.position = 0
  );
