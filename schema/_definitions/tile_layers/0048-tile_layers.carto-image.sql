/* Carto polygons and lines for the image tileserver, drawn from the compilation
   system rather than the materialized `carto.*` build.

   Mapnik reads a PostGIS layer as a subquery it fills per render with the
   `!bbox!` and `!pixel_width!` tokens, so each function takes the box and the
   pixel size as arguments, and the map layer of the carto member for the scale
   being drawn (`map_bounds.face_layer_for('carto', zoom)`), which the legacy
   tileserver resolves once at startup for each scale band.

   The shape is that of the vector route's `faces.sql` (tileserver
   `map_tiles/queries/`), stage for stage, so raster and vector tiles draw the
   same polygons: faces of the layer meeting the box, collected per map; content
   resolved once per map; polygons fetched through the clipped faces and clipped
   to the box; only the ones straddling a face edge cut to the face; one
   simplification pass at half a pixel, with anything under a pixel and a half
   weeded. Change the two together, and benchmark with EXPLAIN (ANALYZE, BUFFERS)
   before changing either: the join through the clipped face is what reaches the
   `(scale, geom)` index of `maps.polygons`. */

CREATE OR REPLACE FUNCTION tile_layers.carto_image_units(
  _bbox geometry,
  _layer_id integer,
  _pixel double precision
) RETURNS TABLE (map_id integer, color text, geom geometry) AS $$
WITH map_bounds AS MATERIALIZED (
  SELECT
    mf.map_id AS source_id,
    ST_UnaryUnion(ST_Collect(ST_ClipByBox2D(mf.geometry, _bbox))) AS geometry
  FROM map_bounds_topology.map_face mf
  WHERE mf.map_layer = _layer_id
    AND ST_Intersects(mf.geometry, _bbox)
    AND map_bounds.has_content(mf.map_id)
  GROUP BY mf.map_id
),
map_content AS MATERIALIZED (
  SELECT
    b.geometry,
    c.source_id AS content_id,
    c.footprint,
    cs.scale AS content_scale
  FROM map_bounds b
  CROSS JOIN LATERAL map_bounds.content_of(b.source_id) c
  JOIN maps.sources cs
    ON cs.source_id = c.source_id
   AND cs.scale = ANY(enum_range(NULL::maps.map_scale)::text[])
),
unit_clipped AS MATERIALIZED (
  SELECT
    p.map_id,
    b.geometry AS face,
    ST_ClipByBox2D(p.geom, _bbox) AS geom
  FROM map_content b
  JOIN maps.polygons p
    ON p.source_id = b.content_id
   AND p.scale = CAST(b.content_scale AS maps.map_scale)
   AND ST_Intersects(p.geom, b.geometry)
  WHERE b.footprint IS NULL OR ST_Contains(b.footprint, ST_PointOnSurface(p.geom))
),
unit_owned AS MATERIALIZED (
  SELECT
    map_id,
    ST_Simplify(
      CASE WHEN ST_Covers(face, ST_Envelope(geom)) THEN geom
           ELSE ST_Intersection(geom, face) END,
      _pixel / 2) AS geom
  FROM unit_clipped
  WHERE geom IS NOT NULL AND NOT ST_IsEmpty(geom)
    AND ST_Area(geom) > (1.5 * _pixel) ^ 2
)
-- Uncolored units are left out, as the `carto.polygons` query always did.
SELECT u.map_id, l.color::text, u.geom
FROM unit_owned u
JOIN maps.map_legend ml ON ml.map_id = u.map_id
JOIN maps.legend l ON l.legend_id = ml.legend_id
WHERE u.geom IS NOT NULL AND NOT ST_IsEmpty(u.geom)
  AND l.color IS NOT NULL AND l.color <> '';
$$ LANGUAGE SQL STABLE;

CREATE OR REPLACE FUNCTION tile_layers.carto_image_lines(
  _bbox geometry,
  _layer_id integer,
  _pixel double precision
) RETURNS TABLE (line_id integer, direction text, "type" text, geom geometry) AS $$
WITH map_bounds AS MATERIALIZED (
  SELECT
    mf.map_id AS source_id,
    ST_UnaryUnion(ST_Collect(ST_ClipByBox2D(mf.geometry, _bbox))) AS geometry
  FROM map_bounds_topology.map_face mf
  WHERE mf.map_layer = _layer_id
    AND ST_Intersects(mf.geometry, _bbox)
    AND map_bounds.has_content(mf.map_id)
  GROUP BY mf.map_id
),
map_content AS MATERIALIZED (
  SELECT
    b.geometry,
    c.source_id AS content_id,
    c.footprint,
    cs.scale AS content_scale
  FROM map_bounds b
  CROSS JOIN LATERAL map_bounds.content_of(b.source_id) c
  JOIN maps.sources cs
    ON cs.source_id = c.source_id
   AND cs.scale = ANY(enum_range(NULL::maps.map_scale)::text[])
),
line_clipped AS MATERIALIZED (
  SELECT
    l.line_id,
    b.geometry AS face,
    coalesce(l.direction, '') AS direction,
    coalesce(l.type, '') AS "type",
    ST_ClipByBox2D(l.geom, _bbox) AS geom
  FROM map_content b
  JOIN maps.lines l
    ON l.source_id = b.content_id
   AND l.scale = CAST(b.content_scale AS maps.map_scale)
   AND ST_Intersects(l.geom, b.geometry)
  WHERE b.footprint IS NULL OR ST_Contains(b.footprint, ST_PointOnSurface(l.geom))
)
SELECT
  line_id,
  direction::text,
  "type"::text,
  ST_Simplify(
    CASE WHEN ST_Covers(face, ST_Envelope(geom)) THEN geom
         ELSE ST_Intersection(geom, face) END,
    _pixel / 2) AS geom
FROM line_clipped
WHERE geom IS NOT NULL AND NOT ST_IsEmpty(geom)
  AND ST_Length(geom) > 1.5 * _pixel;
$$ LANGUAGE SQL STABLE;
