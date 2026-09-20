/* Solved faces, attributed at the level the request asked about.

   Faces are materialised per served layer, so a compilation that is not one
   borrows the faces of the layer it sits in, filtered to the maps it resolves to.

   Ownership and attribution are two different levels, and only one of them is in
   `map_face`. A face is always owned by the map that was solved into the layer --
   a leaf. It is *attributed*, by default, to the compilation it is reached
   through (`via`): from `carto-medium`, an `ngs-alabama` face reads as
   `ngs-bedrock`. `expand` attributes it to the owning map instead.

   For a map sitting directly in the layer the two coincide, which is why joining
   faces on `via` worked for every flat member and silently dropped every map
   under a nested compilation -- all 142 under `ngs-bedrock` and `ngs-surface`
   vanished from the layer. Join on the owner; attribute afterwards.
*/
WITH tile AS (
  SELECT
    ST_TileEnvelope(:z, :x, :y) AS mercator_bbox,
    tile_layers.geographic_envelope(:x, :y, :z, 0.01) AS projected_bbox
), root AS (
  SELECT
    map_bounds.compilation_id(:map_layer) AS source_id,
    map_bounds.face_layer_for(map_bounds.compilation_id(:map_layer)) AS face_layer
), resolved AS (
  /* Where resolution *stops* is where the faces are. A compilation with content
     of its own owns its faces directly -- its members own none, which is what
     materializing means -- so descending past it finds nothing. That is true of
     `bc-surface` (derived) and `sgmc` (ingested) alike, and of a plain map
     targeted by name.

     `expand` is the request to descend anyway, and it is allowed to come back
     empty: a mosaic member owns no face, and saying so is more honest than
     attributing the parent's. Asked for by name, it gets its footprint (below). */
  SELECT root.source_id, root.source_id AS via
  FROM root
  WHERE NOT :expand
    AND map_bounds.has_content(root.source_id)
  UNION ALL
  SELECT l.source_id, l.via
  FROM root
  CROSS JOIN LATERAL map_bounds.compilation_leaves(root.source_id, :expand) l
  WHERE :expand
     OR NOT map_bounds.has_content(root.source_id)
), map_faces AS (
  (SELECT
    DISTINCT ON (f.id)
    f.id AS face_id,
    CASE WHEN :expand THEN r.source_id ELSE r.via END AS source_id,
    CASE WHEN :expand THEN s.name ELSE v.name END AS name,
    CASE WHEN :expand THEN s.slug ELSE v.slug END AS slug,
    s.scale,
    f.map_layer,
    tile_layers.tile_geom(
      ST_Intersection(f.geometry, tile.projected_bbox),
      tile.mercator_bbox
    ) AS geom
  FROM root
  JOIN map_bounds_topology.map_face f ON f.map_layer = root.face_layer
  JOIN tile ON ST_Intersects(f.geometry, tile.projected_bbox)
  -- The owner, always: `via` is an attribution level and a nested compilation
  -- owns no faces of its own.
  JOIN resolved r ON f.map_id = r.source_id
  LEFT JOIN maps.sources s ON s.source_id = r.source_id
  LEFT JOIN maps.sources v ON v.source_id = r.via)
  UNION ALL
  /* A mosaic member has no face of its own: its extent *is* its footprint, read
     straight from `map_area`, as one pseudo-face. Only while nothing topological
     has placed it -- placed, it owns real faces in its layer, found above, and
     this must not double them. */
  (SELECT
    -root.source_id AS face_id,
    root.source_id,
    s.name,
    s.slug,
    s.scale,
    ma.map_layer,
    tile_layers.tile_geom(
      ST_Intersection(ma.geometry, tile.projected_bbox),
      tile.mercator_bbox
    ) AS geom
  FROM root
  JOIN maps.sources s ON s.source_id = root.source_id
  JOIN map_bounds.map_area ma ON ma.source_id = root.source_id
  JOIN tile ON ST_Intersects(ma.geometry, tile.projected_bbox)
  WHERE map_bounds.is_mosaic_member(root.source_id)
    AND NOT EXISTS (
      SELECT 1 FROM map_bounds_topology.map_face f
      WHERE f.map_id = root.source_id AND f.map_layer = root.face_layer
    ))
)
SELECT ST_AsMVT(map_faces, 'map_faces', 4096, 'geom') FROM map_faces;
