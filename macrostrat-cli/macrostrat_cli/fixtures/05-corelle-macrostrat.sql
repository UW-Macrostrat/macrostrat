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
SELECT
	p.map_id,
	p.scale,
	pp.model_id model_id,
	pp.plate_id,
	CASE WHEN ST_Covers(pp.geometry, ST_Union(p.geom)) THEN
		NULL  
	ELSE
		ST_Intersection(pp.geometry, ST_Union(p.geom))
	END AS geom
FROM carto.polygons p
JOIN corelle.plate_polygon pp
  ON ST_Intersects(pp.geometry, p.geom)
JOIN corelle.model m
  ON m.id = pp.model_id
GROUP BY map_id, scale, pp.model_id, pp.geometry, plate_id;

ALTER TABLE corelle_macrostrat.carto_plate_index
ADD CONSTRAINT carto_plate_index_pkey PRIMARY KEY (map_id, scale, model_id, plate_id);

CREATE INDEX carto_plate_index_model_plate_scale_idx ON corelle_macrostrat.carto_plate_index(model_id, plate_id, scale);
CREATE INDEX carto_plate_index_geom_idx ON corelle_macrostrat.carto_plate_index USING gist (geom);

-- Adjust layers to have simplified geometries for rapid filtering
-- This should maybe be moved to Corelle
ALTER TABLE corelle.plate_polygon ADD COLUMN geom_simple geometry(MultiPolygon, 4326);
ALTER TABLE corelle.rotation_cache ADD COLUMN geom geometry(MultiPolygon, 4326);

UPDATE corelle.plate_polygon SET
  geom_simple = ST_Multi(ST_Simplify(ST_Buffer(geometry, 0.25), 0.25))
WHERE geom_simple IS NULL;

UPDATE corelle.rotation_cache rc SET
  geom = ST_CollectionExtract(corelle_macrostrat.rotate(geom_simple, rotation, true), 3)
FROM corelle.plate_polygon pp
WHERE pp.model_id = rc.model_id
  AND pp.plate_id = rc.plate_id
  AND geom IS null;

CREATE INDEX rotation_cache_geom_idx ON corelle.rotation_cache USING gist (geom);

CREATE OR REPLACE FUNCTION corelle_macrostrat.carto_slim_rotated_v1(
  -- bounding box
  x integer,
  y integer,
  z integer,
  -- additional parameters
  query_params json
)
RETURNS bytea
AS $$
DECLARE
srid integer;
features record;
mapsize text;
linesize text[];
mercator_bbox geometry;
min_feature_size numeric;
tile_width numeric;
bedrock bytea;
lines bytea;
_t_step integer;
_model_id integer;
BEGIN

-- Get the time step and model requested from the query parameters
SELECT
  coalesce((query_params->>'t_step')::integer, 0) AS _t_step,
  (query_params->>'model_id')::integer AS _model_id
INTO _t_step, _model_id;

IF _t_step = 0 THEN
  /* Just return the basic map layer */
  return tile_layers.carto_slim(x, y, z, query_params);
END IF;

IF _model_id IS NULL THEN
  RAISE EXCEPTION 'model_id is required';
END IF;

IF z < 3 THEN
  -- Select from carto.tiny table
  mapsize := 'tiny';
  linesize := ARRAY['tiny'];
ELSIF z < 6 THEN
  mapsize := 'small';
  linesize := ARRAY['tiny', 'small'];
ELSIF z < 9 THEN
  mapsize := 'medium';
  linesize := ARRAY['small', 'medium'];
ELSE
  mapsize := 'large';
  linesize := ARRAY['medium', 'large'];
END IF;

--wrap_bbox := NOT z = 0;

-- Units
WITH rotation_info AS (
  SELECT
    pp.model_id,
    pp.plate_id,
    pp.geometry,
    rc.rotation,
    rc.t_step,
    -- Get the tile bounding box rotated to the actual position of the plate on the modern globe
    corelle_macrostrat.tile_envelope(rotation, x, y, z) tile_envelope
  FROM corelle.plate_polygon pp
  JOIN corelle.rotation_cache rc
    ON rc.model_id = pp.model_id
   AND rc.plate_id = pp.plate_id
  WHERE pp.model_id = _model_id
  	AND t_step = _t_step
    AND pp.geometry && corelle_macrostrat.tile_envelope(rotation, x, y, z)
    --AND ST_Intersects(pp.geometry, corelle_macrostrat.tile_envelope(rotation, x, y, z))
),
plate_polygons AS (
  SELECT
    plate_id,
    t_step,
    corelle_macrostrat.build_tile_geom(
      ri.geometry, ri.rotation, x, y, z
    ) geom
  FROM rotation_info ri
),
u1 AS (
  SELECT ST_AsMVT(pp, 'plates') mvt1
  FROM plate_polygons pp
)
SELECT mvt1 AS mvt
FROM u1
INTO bedrock; --, plate_polygons;

RETURN bedrock;

END;
$$ LANGUAGE plpgsql VOLATILE;


CREATE OR REPLACE FUNCTION corelle_macrostrat.tile_envelope(
  rotation numeric[],
  x integer,
  y integer,
  z integer
) RETURNS geometry AS $$
    -- I feel like this bbox needs to be inverted but it seems to work better if not...
  SELECT corelle_macrostrat.rotate(
    --ST_Transform(mercator_bbox, 4326),
    ST_Transform(ST_TileEnvelope(z, x, y), 4326),
    corelle.invert_rotation(rotation),
    true
  );
$$ LANGUAGE sql STABLE;

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
  IF wrap AND ST_XMin(g1) < -150 AND ST_XMax(g1) > 150 THEN
    g1 := ST_WrapX(
      ST_Split(
        ST_MakeValid(ST_ShiftLongitude(g1)),
        -- Antimeridian
        ST_GeomFromText('LINESTRING(180 -90, 180 90)', 4326)
      ),
      180,
      -360
    );
  END IF;
  RETURN g1;
EXCEPTION WHEN OTHERS THEN
   RETURN null;
END;
$$ LANGUAGE plpgsql STABLE;

-- Drop outdated functions
--DROP FUNCTION IF EXISTS corelle_macrostrat.rotate(geometry, numeric[], boolean);
DROP FUNCTION IF EXISTS corelle_macrostrat.rotated_web_mercator_proj(numeric[]);



CREATE OR REPLACE FUNCTION corelle_macrostrat.carto_slim_rotated(
  -- bounding box
  x integer,
  y integer,
  z integer,
  -- additional parameters
  query_params json
)
RETURNS bytea
AS $$
DECLARE
srid integer;
features record;
mapsize map_scale;
linesize text[];
mercator_bbox geometry;
min_feature_size numeric;
tile_width numeric;
bedrock bytea;
lines bytea;
_t_step integer;
_model_id integer;
BEGIN

-- Get the time step and model requested from the query parameters
SELECT
  coalesce((query_params->>'t_step')::integer, 0) AS _t_step,
  (query_params->>'model_id')::integer AS _model_id
INTO _t_step, _model_id;

IF _t_step = 0 THEN
  /* Just return the basic map layer */
  return tile_layers.carto_slim(x, y, z, query_params);
END IF;

IF _model_id IS NULL THEN
  RAISE EXCEPTION 'model_id is required';
END IF;

IF z < 3 THEN
  -- Select from carto.tiny table
  mapsize := 'tiny';
  linesize := ARRAY['tiny'];
ELSIF z < 6 THEN
  mapsize := 'small';
  linesize := ARRAY['tiny', 'small'];
ELSIF z < 9 THEN
  mapsize := 'medium';
  linesize := ARRAY['small', 'medium'];
ELSE
  mapsize := 'large';
  linesize := ARRAY['medium', 'large'];
END IF;

--wrap_bbox := NOT z = 0;

-- Units
WITH rotation_info AS (
  SELECT
    pp.plate_id,
    pp.model_id,
    -- Get the tile bounding box rotated to the actual position of the plate on the modern globe
    --ST_Area(corelle_macrostrat.tile_envelope(rc.rotation, t.x, t.y, t.z)::geography)/ST_Area(ST_Transform(tile_utils.envelope(t.x, t.y, t.z), 4326)::geography) tile_area_ratio,
    geometry geom,
    corelle.rotate_geometry(ST_Transform(tile_utils.envelope(x, y, z), 4326), corelle.invert_rotation(rc.rotation)) tile_geom,
    rc.rotation rotation
  FROM corelle.plate_polygon pp
  JOIN corelle.rotation_cache rc
    ON rc.plate_id = pp.plate_id
    AND rc.model_id = pp.model_id
    AND rc.t_step = _t_step
  WHERE rc.model_id = _model_id
    AND coalesce(pp.old_lim, 4000) >= _t_step
    AND coalesce(pp.young_lim, 0) <= _t_step
   AND pp.model_id = _model_id
),
relevant_plates AS (
  SELECT *
  FROM rotation_info
  WHERE ST_Intersects(geom::geography, tile_geom::geography)
),
units AS (
  SELECT
    p.plate_id,
    p.model_id,
    '#888888' AS color,
    corelle_macrostrat.build_tile_geom(
      p.geom, p.rotation, x, y, z
    ) geom 
  FROM relevant_plates p

  -- SELECT DISTINCT ON (u.map_id)
  --   u.map_id,
  --   u.source_id,
  --   cpi.plate_id,
  --   cpi.model_id,
  --   corelle_macrostrat.build_tile_geom(
  --     coalesce(cpi.geom, u.geom), ri.rotation, x, y, z
  --   ) geom
  -- FROM carto.polygons u
  -- JOIN corelle_macrostrat.carto_plate_index cpi
  --   ON cpi.map_id = u.map_id
  --  AND cpi.scale = u.scale
  --  AND cpi.model_id = _model_id
  -- JOIN relevant_plates ri
  --   ON ri.plate_id = cpi.plate_id
  --  AND ST_Intersects(coalesce(cpi.geom, u.geom)::geography, ri.tile_geom)
  --   AND u.scale = mapsize
)
SELECT ST_AsMVT(units) AS mvt
FROM units
INTO bedrock; --, plate_polygons;

RETURN bedrock;

END;
$$ LANGUAGE plpgsql VOLATILE;



CREATE OR REPLACE FUNCTION corelle_macrostrat.tile_envelope(
  rotation numeric[],
  x integer,
  y integer,
  z integer
) RETURNS geometry AS $$
  SELECT corelle_macrostrat.rotate(
    --ST_Transform(mercator_bbox, 4326),
    ST_Transform(ST_Segmentize(tile_utils.envelope(x, y, z), tile_utils.tile_width(z)/8), 4326),
    corelle.invert_rotation(rotation),
    false
  );
$$ LANGUAGE sql STABLE PARALLEL SAFE;

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
  mercator_bbox geometry;
  proj4text text;
  proj_additions text;
  wrap numeric = 0;
  tile_geom geometry;
  tms_width numeric;
  meridian geometry;
  shifted geometry;
BEGIN
  mercator_bbox := tile_utils.envelope(_x,_y,_z);
  tms_width := tile_utils.tile_width(0);

  -- Pre-simplify the geometry to reduce the size of the tile
  geom := ST_SnapToGrid(geom, 0.001/pow(2,_z));

  IF true THEN
    tile_geom := ST_Transform(corelle_macrostrat.rotate(geom, rotation, true), 3857);
  ELSE
    proj4text := corelle.build_proj_string(
      rotation,
      '+o_proj=merc +R=6378137 +over'
    );
    tile_geom := ST_SetSRID(ST_Transform(geom, proj4text), 3857); 
  END IF;

  RETURN ST_Simplify(
    ST_AsMVTGeom(
      tile_geom,
      mercator_bbox,
      4096,
      12,
      true
    ),
    8
  );
END;
$$ LANGUAGE plpgsql STABLE PARALLEL SAFE;

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
  IF wrap AND ST_XMin(g1) < -150 AND ST_XMax(g1) > 150 THEN
    g1 := ST_WrapX(
      ST_Split(
        ST_MakeValid(ST_ShiftLongitude(g1)),
        -- Antimeridian
        ST_GeomFromText('LINESTRING(180 -90, 180 90)', 4326)
      ),
      180,
      -360
    );
  END IF;
  RETURN g1;
END;
$$ LANGUAGE plpgsql STABLE;

-- Drop outdated functions
DROP FUNCTION IF EXISTS corelle_macrostrat.rotate(geometry, numeric[], boolean);
DROP FUNCTION IF EXISTS corelle_macrostrat.rotated_web_mercator_proj(numeric[]);