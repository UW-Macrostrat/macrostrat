/** Create one `maps.sources` row per SGMC constituent map.

  `sources.sgmc_polygons` is the raw USGS staging table, kept from ingestion. It
  carries the structured provenance that `maps.legend.comments` only paraphrases:
  `ref_id` names the published map, `reference` its citation, `digital_ur` its
  URL. Sixty-six `ref_id`s are staged; `IL003` lost its only polygon at ingest,
  so the sixty-five that actually carry geometry become sources.

  Grouped by `ref_id` alone, not by `(state, ref_id)`: a member is a *published
  map*, and `VT001` -- the Vermont bedrock map -- crosses into NH and NY. One map
  is one source however many states it touches.

  Names are deliberately mechanical. The citations are heterogeneous enough that
  no regex recovers a title reliably -- roughly half yield something usable and
  the rest yield fragments like "10 p., 2 DOS HD disks" -- and inconsistent names
  read worse than uniform ones. The citation itself goes to `ref_title`, which is
  unbounded, and a client that wants a prettier label can render it.
*/
INSERT INTO maps.sources (
  slug, name, scale, status_code, is_finalized, url, ref_title, ref_compilation)
SELECT
  lower('sgmc-' || g.ref_id),
  -- `maps.sources.name` is varchar(255); the state list keeps it recognisable.
  left(
    'SGMC ' || g.ref_id || ' (' || string_agg(DISTINCT g.state, ', ') || ')',
    255
  ),
  'medium'::maps.map_scale,
  'active',
  -- Documentary: it holds no polygons, and `is_finalized` is what
  -- `holds_polygons` reads.
  false,
  max(g.digital_ur),
  max(g.reference),
  -- The programme these were published under, in the bibliographic sense --
  -- separate from the `compilation_member` edge that records what SGMC is
  -- assembled from.
  'SGMC'
FROM sources.sgmc_polygons g
JOIN maps.polygons p ON p.orig_id::integer = g._pkid AND p.source_id = 133
GROUP BY g.ref_id
ON CONFLICT (slug) DO NOTHING;
