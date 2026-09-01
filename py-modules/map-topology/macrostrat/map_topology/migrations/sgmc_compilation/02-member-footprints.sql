/** Give each constituent a footprint.

  `ST_CoverageUnion` rather than `ST_Union`: SGMC's polygons are a coverage --
  verified, zero overlapping pairs in a 3,000-polygon sample -- so the coverage
  form applies, and it runs the whole set in ~24s against ~4 minutes for
  `ST_Union`. The output is identical.

  These rows exist so the constituents can be found spatially and drawn as
  footprints. They are never parted out: `get_map_list` excludes documentary
  members, which is the entire reason this approach costs nothing in the
  topology. Noding all sixty-five measures at +30% on total topology linework
  (983,404 simplified boundary points against `map_topo`'s current 3,308,335).

  Their union comes to ~7.84M km² against SGMC's own boundary of 8.48M -- the
  authored outline is looser than the polygons it contains, which is expected and
  is why the members' footprints are derived from polygons rather than clipped
  out of the parent.
*/
INSERT INTO map_bounds.map_area (id, geometry, map_layer)
SELECT
  s.source_id,
  ST_Multi(ST_CoverageUnion(p.geom)),
  map_bounds.layer_id('medium')
FROM sources.sgmc_polygons g
JOIN maps.polygons p ON p.orig_id::integer = g._pkid AND p.source_id = 133
JOIN maps.sources s ON s.slug = lower('sgmc-' || g.ref_id)
GROUP BY s.source_id
ON CONFLICT (id) DO NOTHING;

UPDATE map_bounds.map_area a
SET area_km = ST_Area(ST_Segmentize(a.geometry, 90)::geography) / 1e6
FROM maps.sources s
WHERE s.source_id = a.source_id
  AND s.slug LIKE 'sgmc-%'
  AND a.area_km IS NULL;
