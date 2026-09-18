WITH tile AS (
    SELECT
      ST_TileEnvelope(:z, :x, :y) AS mercator_bbox,
      tile_layers.geographic_envelope(:x, :y, :z, 0.01) AS projected_bbox,
      CASE WHEN :z < 3 THEN 'tiny'
           WHEN :z < 6 THEN 'carto-small'
           WHEN :z < 9 THEN 'carto-medium'
           ELSE 'carto-large'
      END AS layer_slug
),
map_bounds AS (
  SELECT
    mf.map_id AS source_id,
    ST_Intersection(mf.geometry, tile.projected_bbox) AS geometry,
    tile.mercator_bbox
  FROM map_bounds_topology.map_face mf
  JOIN tile
    ON ST_Intersects(mf.geometry, tile.projected_bbox)
  WHERE mf.map_layer = map_bounds.layer_id(tile.layer_slug)
),
/* Which polygons fill a face is `map_bounds.polygons_of`'s question: the face's
   owner need not hold them -- a mosaic member placed in a layer (Nevada from SGMC
   at `large`) shows its parent's polygons inside its footprint. The function also
   prunes the partition by the content's scale, not the owner's. */
unit_features AS (
  SELECT
    p.map_id,
    b.source_id,
    l.*, -- legend info
    -- TODO: only run intersection if the map is partially visible
    tile_layers.tile_geom(ST_Intersection(p.geom, b.geometry), b.mercator_bbox) AS geom
  FROM map_bounds b
  CROSS JOIN LATERAL map_bounds.polygons_of(b.source_id, b.geometry) p
  JOIN maps.map_legend
    ON p.map_id = map_legend.map_id
  JOIN tile_layers.map_legend_info AS l
    ON l.legend_id = map_legend.legend_id
),
-- Lines
line_features AS (
  SELECT
    l.line_id,
    b.source_id,
    coalesce(l.descrip, '') AS descrip,
    coalesce(l.name, '') AS name,
    coalesce(l.direction, '') AS direction,
    coalesce(l.type, '') AS "type",
    cs.lines_oriented AS oriented,
    tile_layers.tile_geom(ST_Intersection(l.geom, b.geometry), b.mercator_bbox) AS geom
  FROM map_bounds b
  CROSS JOIN LATERAL map_bounds.lines_of(b.source_id, b.geometry) l
  -- `lines_oriented` belongs to whoever holds the lines.
  JOIN maps.sources cs ON cs.source_id = l.source_id
), units_tile AS (
  SELECT ST_AsMVT(unit_features, 'units') AS units
  FROM unit_features
), lines_tile AS (
  SELECT ST_AsMVT(line_features, 'lines') AS lines
  FROM line_features
)
SELECT units || lines
FROM units_tile, lines_tile;
