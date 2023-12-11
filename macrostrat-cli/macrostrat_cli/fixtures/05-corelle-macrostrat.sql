CREATE SCHEMA IF NOT EXISTS corelle_macrostrat;

--DROP MATERIALIZED VIEW IF EXISTS corelle_macrostrat.carto_plate_index;


CREATE MATERIALIZED VIEW IF NOT EXISTS corelle_macrostrat.natural_earth_index AS
SELECT
  f.id,
  properties ->> 'scalerank' AS scalerank,
  ST_Intersection(f.geometry, pp.geometry) geometry,
  model_id,
  plate_id
FROM corelle.feature f
JOIN corelle.plate_polygon pp
  ON ST_Intersects(f.geometry, pp.geometry)
WHERE dataset_id = 'ne_110m_land';

CREATE MATERIALIZED VIEW IF NOT EXISTS corelle_macrostrat.column_index AS
SELECT
	col_id,
	model_id,
	plate_id
FROM macrostrat.col_areas c
JOIN corelle.plate_polygon pp
  ON ST_Intersects(ST_Centroid(col_area), pp.geometry);

-- carto plate index
CREATE TABLE IF NOT EXISTS corelle_macrostrat.carto_plate_index AS
WITH plates AS (
SELECT
	plate_id,
	model_id,
	ST_Union(pp.geometry) geom
FROM corelle.plate_polygon pp
GROUP BY plate_id, model_id
)
SELECT DISTINCT ON (map_id, plate_id, model_id, geom_scale)
  map_id,
  pp.plate_id,
  pp.model_id,
  geom_scale scale
FROM carto.polygons p
JOIN plates pp
  ON ST_Intersects(p.geom, pp.geom);


ALTER TABLE corelle_macrostrat.carto_plate_index
ADD CONSTRAINT carto_plate_index_pkey PRIMARY KEY (map_id, model_id, scale);

-- CREATE INDEX carto_plate_index_model_plate_scale_idx ON corelle_macrostrat.carto_plate_index(model_id, plate_id, scale);

CREATE OR REPLACE FUNCTION corelle_macrostrat.tile_envelope(
  rotation numeric[],
  x integer,
  y integer,
  z integer
) RETURNS geometry AS $$
DECLARE
  modern_bbox geometry;
BEGIN
  modern_bbox := ST_Transform(ST_TileEnvelope(z, x, y), 4326);
  -- I feel like this bbox needs to be inverted but it seems to work better if not...
  RETURN corelle_macrostrat.rotate(
    modern_bbox,
    corelle.invert_rotation(rotation),
    false
  );
END;
$$ LANGUAGE plpgsql VOLATILE;

CREATE OR REPLACE FUNCTION corelle_macrostrat.build_tile_geom(
  geom geometry,
  rotation numeric[],
  _x integer,
  _y integer,
  _z integer
)
RETURNS geometry
AS $$
DECLARE
  tile_geom geometry;
BEGIN
  -- Pre-simplify the geometry to reduce the size of the tile
  --geom := ST_SnapToGrid(geom, 0.001/pow(2,_z));
  tile_geom := corelle_macrostrat.rotate(geom, rotation, true);

  --END IF;

  --tile_geom := ST_WrapX(tile_geom, 0, wrap);

  RETURN ST_Simplify(
    ST_AsMVTGeom(
      ST_Transform(
        tile_geom,
        3857
      ),
      ST_TileEnvelope(_z,_x,_y),
      4096,
      12,
      true
    ),
    8
  );
END;
$$ LANGUAGE plpgsql STABLE; 

CREATE OR REPLACE FUNCTION corelle_macrostrat.antimeridian_split(
  geom geometry
) RETURNS geometry AS $$
DECLARE
  g1 geometry;
  meridian geometry;
BEGIN
  g1 := ST_MakeValid(geom);
  g1 := ST_WrapX(g1, -180, 180);
  g1 := ST_WrapX(g1, 180, -180);
  RETURN g1;
EXCEPTION WHEN OTHERS THEN
  RETURN null;
END;
$$ LANGUAGE plpgsql STABLE;


CREATE OR REPLACE FUNCTION corelle_macrostrat.rotate(
  geom geometry,
  rotation double precision[],
  wrap boolean DEFAULT false
) RETURNS geometry AS $$
DECLARE
  g1 geometry;
BEGIN
  g1 := corelle.rotate_geometry(geom, rotation);
  -- Heuristic to determine if the geometry crosses the antimeridian
  -- https://gis.stackexchange.com/questions/182728/how-can-i-convert-postgis-geography-to-geometry-and-split-polygons-that-cross-th
  -- https://macwright.com/2016/09/26/the-180th-meridian.html
  -- This has to be run for each tile, because a lot of geometries that
  -- don't properly intersect the tile are still included due to polygon winding effects.
  -- We really should figure out how to exclude geometries with no points
  -- in the tile envelope, so we don't have to run this check on every tile
  RETURN corelle_macrostrat.antimeridian_split(g1);
END;
$$ LANGUAGE plpgsql VOLATILE;

CREATE OR REPLACE FUNCTION corelle_macrostrat.rotate_to_web_mercator(
  geom geometry,
  rotation double precision[],
  wrap boolean DEFAULT false
) RETURNS geometry AS $$
DECLARE
  proj_string text;
  proj_string2 text;
  g1 geometry;
  g2 geometry;
  threshold double precision;
  new_rotation double precision[];
BEGIN
  proj_string := corelle.build_proj_string(rotation, '+R=6378137 +o_proj=merc ');
  g1 := ST_SetSRID(ST_Transform(geom, proj_string), 3857);

  threshold := pi() * 6378137;

  IF ST_XMax(g1) - ST_XMin(g1) > 1.8 * threshold THEN
    -- Rotate to the other side of the globe
    proj_string := corelle.build_proj_string(rotation, '+R=6378137 +o_proj=merc ', pi());
    g1 := ST_SetSRID(ST_Transform(geom, proj_string), 3857);
    g1 := ST_Union(
      ST_Translate(g1, -threshold, 0),
      ST_Translate(g1, threshold, 0)
    );
  END IF;
  RETURN g1;
EXCEPTION WHEN OTHERS THEN
  RETURN null;
END;
$$ LANGUAGE plpgsql VOLATILE;

-- Drop outdated functions
DROP FUNCTION IF EXISTS corelle_macrostrat.rotate(geometry, numeric[], boolean);
DROP FUNCTION IF EXISTS corelle_macrostrat.rotated_web_mercator_proj(numeric[]);