/** Declare SGMC a compilation whose content was ingested.

  Priority is uniform: the constituents mosaic rather than overlap, so there is
  nothing for priority to resolve. It is recorded as `disjoint` for the same
  reason.

  Order matters -- `content` is set *before* the membership edges exist.
  The moment SGMC has members, `sync-compilation-bounds` would clear its
  topogeometry, and nothing would rebuild it: `compilation_assembly` inner-joins
  members on `topo IS NOT NULL`, and documentary members have none. SGMC would
  lose its 12,787 primitive faces and the conterminous US would lose its identity
  in `medium`, silently.
*/
INSERT INTO map_bounds.compilation (source_id, content, assembly_mode, note)
VALUES (
  133,
  'ingested',
  'disjoint',
  'Constituents are documentary: the USGS source maps SGMC was compiled from, '
  'recovered from sources.sgmc_polygons. SGMC holds the polygons.'
)
ON CONFLICT (source_id) DO UPDATE
  SET content = EXCLUDED.content,
      assembly_mode = EXCLUDED.assembly_mode,
      note = EXCLUDED.note;

INSERT INTO map_bounds.compilation_member (compilation_id, member_id, priority, role)
SELECT 133, s.source_id, 0, 'constituent'
FROM maps.sources s
WHERE s.slug LIKE 'sgmc-%'
ON CONFLICT (compilation_id, member_id) DO NOTHING;
