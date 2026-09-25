/* Bounds of a compilation's members.

   `level=member` (the default) draws the members the compilation presents:
   descending through registered compilations, which are structural and carry
   only envelopes, and stopping at the first real compilation or map. British
   Columbia appears once, as `bc-surface`, rather than as its two maps.
   `level=map` draws the maps at the bottom instead -- the referenceable units of
   mapping -- which is a different and equally legitimate question.
*/
WITH tile AS (
  SELECT
    ST_TileEnvelope(:z, :x, :y) AS mercator_bbox,
    tile_layers.geographic_envelope(:x, :y, :z, 0.01) AS projected_envelope
), root AS (
  SELECT map_bounds.source_id(:map_layer) AS source_id
), members AS (
  -- The member each resolved map belongs to. Not the *direct* members: those are
  -- `medium` and `large`, structural layers carrying only an envelope.
  SELECT DISTINCT r.member_id AS source_id, r.member_id
  FROM root
  CROSS JOIN LATERAL map_bounds.resolved_maps(root.source_id) r
  WHERE :level <> 'map'
  UNION
  -- Every map at the bottom, whether or not something above it is materialized.
  SELECT m.source_id, m.source_id
  FROM root
  CROSS JOIN LATERAL map_bounds.members_of(root.source_id, true) m
  WHERE :level = 'map'
    AND NOT map_bounds.is_compilation(m.source_id)
  UNION
  -- A map with nothing beneath it is its own bounds, so any source is
  -- addressable by name -- `bc_2017` and `sgmc-nv001` as much as `carto-large`.
  -- Without this the route is silently empty for every map.
  SELECT root.source_id, root.source_id
  FROM root
  WHERE NOT map_bounds.is_compilation(root.source_id)
), sources AS (
  SELECT
    s.source_id,
    s.name,
    s.slug,
    s.scale,
    m.member_id,
    v.slug AS member_slug,
    tile_layers.tile_geom(
      ST_Intersection(ma.geometry, tile.projected_envelope),
      tile.mercator_bbox
    ) AS geom
  FROM members m
  JOIN map_bounds.map_area ma ON ma.source_id = m.source_id
  JOIN maps.sources s ON s.source_id = m.source_id
  LEFT JOIN maps.sources v ON v.source_id = m.member_id
  CROSS JOIN tile
  WHERE ST_Intersects(ma.geometry, tile.projected_envelope)
)
SELECT ST_AsMVT(sources, 'maps', 4096, 'geom') FROM sources;
