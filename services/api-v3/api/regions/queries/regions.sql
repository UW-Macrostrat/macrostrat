/* Regions without their geometry: the tileserver draws them (`/regions/tiles`).
   The bounding box comes from the geometry header, so no polygon is read. */
SELECT
  b.boundary_id AS region_id,
  b.source_id,
  b.name,
  b.boundary_group AS region_group,
  b.boundary_type AS region_type,
  initcap(b.boundary_class) AS region_class,
  ARRAY[
    round(ST_XMin(box.extent)::numeric, 4),
    round(ST_YMin(box.extent)::numeric, 4),
    round(ST_XMax(box.extent)::numeric, 4),
    round(ST_YMax(box.extent)::numeric, 4)
  ]::float[] AS bounds
FROM geologic_boundaries.boundaries b
CROSS JOIN LATERAL (SELECT Box2D(b.geom) AS extent) box
WHERE CAST(:source_id AS integer) IS NULL
   OR b.source_id = CAST(:source_id AS integer)
ORDER BY b.name, b.boundary_id
