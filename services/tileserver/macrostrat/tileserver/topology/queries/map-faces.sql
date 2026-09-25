/* Solved faces, attributed at the level the request asked about.

   Faces are cached per registered compilation, so a compilation that is not one
   borrows the faces of the registered compilation it belongs to, filtered to the
   maps it resolves to (interim, until every served compilation has its own).

   Ownership and attribution are two different levels, and only one of them is in
   `map_face`. A face is always owned by the map that was solved into the
   compilation -- a resolved map. It is *attributed*, by default, to the member of
   the compilation it belongs to (`level=member`): from `carto-medium`, an
   `ngs-alabama` face reads as `ngs-bedrock`. `level=map` attributes it to the
   owning map instead.

   For a map directly in the compilation the two coincide, which is why joining
   faces on the member worked for every flat member and silently dropped every
   map under a nested compilation. Join on the owner; attribute afterwards.
*/
WITH tile AS (
  SELECT
    ST_TileEnvelope(:z, :x, :y) AS mercator_bbox,
    tile_layers.geographic_envelope(:x, :y, :z, 0.01) AS projected_bbox
), root AS (
  SELECT
    map_bounds.source_id(:map_layer) AS source_id,
    map_bounds.face_layer_for(map_bounds.source_id(:map_layer)) AS face_layer
), resolved AS (
  /* Where resolution *stops* is where the faces are. A compilation with content
     of its own owns its faces directly -- its members own none, which is what
     materializing means -- so descending past it finds nothing. That is true of
     `bc-surface` (derived) and `sgmc` (originals) alike, and of a plain map
     targeted by name.

     `level=map` is the request to descend anyway, and it is allowed to come back
     empty: a mosaic member owns no face, and saying so is more honest than
     attributing the mosaic's. Asked for by name, it gets its bounds (below). */
  SELECT root.source_id AS map_id, root.source_id AS member_id
  FROM root
  WHERE :level <> 'map'
    AND map_bounds.has_content(root.source_id)
  UNION ALL
  SELECT r.map_id, r.member_id
  FROM root
  CROSS JOIN LATERAL map_bounds.resolved_maps(root.source_id) r
  WHERE :level <> 'map'
    AND NOT map_bounds.has_content(root.source_id)
  UNION ALL
  SELECT m.source_id, m.source_id
  FROM root
  CROSS JOIN LATERAL map_bounds.members_of(root.source_id, true) m
  WHERE :level = 'map'
    AND NOT map_bounds.is_compilation(m.source_id)
), map_faces AS (
  (SELECT
    DISTINCT ON (f.id)
    f.id AS face_id,
    CASE WHEN :level = 'map' THEN r.map_id ELSE r.member_id END AS source_id,
    CASE WHEN :level = 'map' THEN s.name ELSE v.name END AS name,
    CASE WHEN :level = 'map' THEN s.slug ELSE v.slug END AS slug,
    s.scale,
    ml.slug AS map_layer,
    f.map_layer AS map_layer_id,
    tile_layers.tile_geom(
      ST_Intersection(f.geometry, tile.projected_bbox),
      tile.mercator_bbox
    ) AS geom
  FROM root
  JOIN map_bounds_topology.map_face f ON f.map_layer = root.face_layer
  JOIN map_bounds.map_layer ml ON ml.id = f.map_layer
  JOIN tile ON ST_Intersects(f.geometry, tile.projected_bbox)
  -- The owner, always: the member is an attribution level and a nested
  -- compilation owns no faces of its own.
  JOIN resolved r ON f.map_id = r.map_id
  LEFT JOIN maps.sources s ON s.source_id = r.map_id
  LEFT JOIN maps.sources v ON v.source_id = r.member_id)
  UNION ALL
  /* A mosaic member has no face of its own: its extent *is* its bounds, read
     straight from `map_area`, as one pseudo-face. Only while nothing topological
     contains it -- as a member of a topological compilation it owns real faces
     there, found above, and this must not double them. */
  (SELECT
    -root.source_id AS face_id,
    root.source_id,
    s.name,
    s.slug,
    s.scale,
    ml.slug AS map_layer,
    ma.map_layer AS map_layer_id,
    tile_layers.tile_geom(
      ST_Intersection(ma.geometry, tile.projected_bbox),
      tile.mercator_bbox
    ) AS geom
  FROM root
  JOIN maps.sources s ON s.source_id = root.source_id
  JOIN map_bounds.map_area ma ON ma.source_id = root.source_id
  LEFT JOIN map_bounds.map_layer ml ON ml.id = ma.map_layer
  JOIN tile ON ST_Intersects(ma.geometry, tile.projected_bbox)
  WHERE map_bounds.is_mosaic_member(root.source_id)
    AND NOT EXISTS (
      SELECT 1 FROM map_bounds_topology.map_face f
      WHERE f.map_id = root.source_id AND f.map_layer = root.face_layer
    ))
)
SELECT ST_AsMVT(map_faces, 'map_faces', 4096, 'geom') FROM map_faces;
