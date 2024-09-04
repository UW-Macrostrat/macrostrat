CREATE OR REPLACE FUNCTION tile_utils.tms_data(tms text = null)
  RETURNS tile_utils.tms_definition
AS $$
  SELECT *
  FROM tile_utils.tms_definition
  WHERE name = coalesce(
    tms,
    tile_utils.default_tms()
  );
$$ LANGUAGE SQL IMMUTABLE;

CREATE OR REPLACE FUNCTION tile_utils.tms_bounds(
  tms text = null
) RETURNS geometry(Polygon)
AS $$
  SELECT (tile_utils.tms_data(tms)).bounds
$$
LANGUAGE SQL IMMUTABLE;

CREATE OR REPLACE FUNCTION tile_utils.tms_srid(tms text = null)
  RETURNS integer
AS $$
  SELECT ST_SRID(tile_utils.tms_bounds(tms));
$$ LANGUAGE SQL IMMUTABLE;

CREATE OR REPLACE FUNCTION tile_utils.tms_geographic_srid(tms text = null)
  RETURNS integer
AS $$
  SELECT coalesce((tile_utils.tms_data(tms)).geographic_srid, 4326);
$$ LANGUAGE SQL IMMUTABLE;


CREATE OR REPLACE FUNCTION tile_utils.envelope(
    _x integer,
    _y integer,
    _z integer,
    _tms text = null
  ) RETURNS geometry(Polygon)
AS $$
  SELECT ST_TileEnvelope(
    _z, _x, _y,
    tile_utils.tms_bounds(_tms)
  );
$$ LANGUAGE SQL IMMUTABLE;

CREATE OR REPLACE FUNCTION tile_utils.tile_width(_z integer, _tms text = null)
/** Tile width in projected coordinates (currently only works for square TMS)*/
RETURNS numeric AS $$
DECLARE
  _tms_bounds geometry;
  _tms_size numeric;
  _tile_size numeric;
BEGIN
  _tms_bounds := tile_utils.tms_bounds(_tms);
  _tms_size := ST_XMax(_tms_bounds) - ST_XMin(_tms_bounds);
  RETURN _tms_size/(2^_z);
END;
$$ LANGUAGE PLPGSQL IMMUTABLE;


-- This currently only works for square tiles.
CREATE OR REPLACE FUNCTION tile_utils.tile_index(
  coord numeric,
  z integer,
  _tms text = null
) RETURNS integer AS $$
  SELECT floor(coord/tile_utils.tile_width(z, _tms))::integer;
$$ LANGUAGE SQL STABLE;


CREATE OR REPLACE FUNCTION tile_utils.containing_tiles(
  _geom geometry,
  _tms text = null
) RETURNS TABLE (
  x integer,
  y integer,
  z integer
) AS $$
DECLARE
  _tms_bounds geometry;
  _geom_bbox box2d;
BEGIN
  _tms_bounds := tile_utils.tms_bounds(_tms);

  IF ST_Within(_geom, ST_Transform(_tms_bounds, ST_SRID(_geom))) THEN
    _geom_bbox := ST_Transform(_geom, ST_SRID(_tms_bounds))::box2d;
  ELSE
    RETURN;
  END IF;

  RETURN QUERY
  WITH tile_sizes AS (
    SELECT
      a.zoom
    FROM generate_series(0, 24) AS a(zoom)
  ), tilebounds AS (
    SELECT t.zoom,
      tile_utils.tile_index((ST_XMin(_geom_bbox)-ST_XMin(_tms_bounds))::numeric, t.zoom) xmin,
      tile_utils.tile_index((ST_YMax(_tms_bounds)-ST_YMin(_geom_bbox))::numeric, t.zoom) ymin,
      tile_utils.tile_index((ST_XMax(_geom_bbox)-ST_XMin(_tms_bounds))::numeric, t.zoom) xmax,
      tile_utils.tile_index((ST_YMax(_tms_bounds)-ST_YMax(_geom_bbox))::numeric, t.zoom) ymax
    FROM tile_sizes t
  )
  SELECT
    t.xmin::integer x,
    t.ymin::integer y,
    t.zoom::integer z
  FROM tilebounds t
  WHERE t.xmin = t.xmax
    AND t.ymin = t.ymax
  ORDER BY z DESC;
END;  
$$ LANGUAGE plpgsql STABLE;


CREATE OR REPLACE FUNCTION tile_utils.parent_tile(
  _geom geometry,
  _tms text = null
) RETURNS TABLE (
  x integer,
  y integer,
  z integer
) AS $$
  SELECT x, y, z FROM tile_utils.containing_tiles(_geom, _tms) LIMIT 1;
$$ LANGUAGE sql STABLE;


CREATE OR REPLACE FUNCTION tile_utils.cluster_expansion_zoom(
  geom geometry,
  zoom integer,
  expanded_pixel_width integer DEFAULT 256
)
/** Returns the zoom level at which the given tile-relative geometry will be expanded to the given pixel width.
  The input geometry must already be in tile pixel coordinates created by ST_AsMVTGeom.
  This is useful for calculating expansion zooms for clustered points.
*/
RETURNS integer AS $$
  DECLARE
    bbox_size double precision;
    zoom_delta double precision;
  BEGIN
    SELECT greatest(ST_XMax(geom) - ST_XMin(geom), ST_YMax(geom)-ST_YMin(geom)) INTO bbox_size;

    IF bbox_size = 0 THEN
      RETURN null;
    END IF;

    zoom_delta := sqrt(expanded_pixel_width/bbox_size);

    RETURN round(zoom + zoom_delta);
  END;
$$ LANGUAGE plpgsql IMMUTABLE;
