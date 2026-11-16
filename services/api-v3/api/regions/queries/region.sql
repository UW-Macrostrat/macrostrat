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
  ]::float[] AS bounds,
  b.descrip AS description,
  b.wiki_link,
  s.name AS source_name,
  s.url,
  s.ref_title,
  s.authors,
  s.ref_year,
  s.ref_source,
  s.isbn_doi,
  s.licence AS license
FROM geologic_boundaries.boundaries b
CROSS JOIN LATERAL (SELECT Box2D(b.geom) AS extent) box
LEFT JOIN geologic_boundaries.sources s ON s.source_id = b.source_id
WHERE b.boundary_id = :region_id
