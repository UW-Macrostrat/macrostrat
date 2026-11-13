SELECT
  s.source_id,
  s.name,
  s.url,
  s.ref_title,
  s.authors,
  s.ref_year,
  s.ref_source,
  s.isbn_doi,
  s.licence AS license,
  count(b.boundary_id) AS n_regions
FROM geologic_boundaries.sources s
LEFT JOIN geologic_boundaries.boundaries b ON b.source_id = s.source_id
GROUP BY s.source_id
ORDER BY s.name
