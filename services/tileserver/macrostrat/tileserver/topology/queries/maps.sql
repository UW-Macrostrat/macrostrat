/* Footprints of a compilation's members.

   By default these are the *units* it presents: descending through served layers,
   which are structural and carry only envelopes, and stopping at the first real
   compilation or map. British Columbia appears once, as `bc-surface`, rather than
   as its two constituent maps. Requesting `expand` returns those constituents
   instead -- the referenceable units of mapping -- which is a different and
   equally legitimate question.
*/
WITH tile AS (
  SELECT
    ST_TileEnvelope(:z, :x, :y) AS mercator_bbox,
    tile_layers.geographic_envelope(:x, :y, :z, 0.01) AS projected_envelope
), root AS (
  SELECT map_bounds.compilation_id(:map_layer) AS source_id
), members AS (
  -- The unit each map is presented as, or the map itself when expanded. Not the
  -- *direct* members: those are `medium` and `large`, structural layers carrying
  -- only an envelope.
  SELECT DISTINCT
    CASE WHEN :expand THEN l.source_id ELSE l.via END AS source_id,
    l.via
  FROM root
  CROSS JOIN LATERAL map_bounds.compilation_leaves(root.source_id, :expand) l
  UNION
  -- A map with nothing beneath it is its own footprint, so any source is
  -- addressable by name -- `bc_2017` and `sgmc-nv001` as much as `carto-large`.
  -- Without this the route is silently empty for every leaf map.
  SELECT root.source_id, root.source_id
  FROM root
  WHERE NOT EXISTS (
    SELECT 1 FROM map_bounds.compilation_member cm
    WHERE cm.compilation_id = root.source_id
  )
), sources AS (
  SELECT
    s.source_id,
    s.name,
    s.slug,
    s.scale,
    v.slug AS via,
    tile_layers.tile_geom(
      ST_Intersection(ma.geometry, tile.projected_envelope),
      tile.mercator_bbox
    ) AS geom
  FROM members m
  JOIN map_bounds.map_area ma ON ma.source_id = m.source_id
  JOIN maps.sources s ON s.source_id = m.source_id
  LEFT JOIN maps.sources v ON v.source_id = m.via
  CROSS JOIN tile
  WHERE ST_Intersects(ma.geometry, tile.projected_envelope)
)
SELECT ST_AsMVT(sources, 'maps', 4096, 'geom') FROM sources;
