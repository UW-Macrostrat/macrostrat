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
ALTER TABLE corelle.plate_polygon ADD COLUMN geom_simple geometry(Geometry, 4326);
ALTER TABLE corelle.rotation_cache ADD COLUMN geom geometry(Geometry, 4326);

UPDATE corelle.plate_polygon SET
  geom_simple = corelle_macrostrat.antimeridian_split(ST_Multi(ST_Simplify(ST_Buffer(geometry, 0.1), 0.1)))
WHERE geom_simple IS NULL;

UPDATE corelle.rotation_cache rc SET
  geom = ST_CollectionExtract(coalesce(corelle_macrostrat.rotate(geom_simple, rotation, true), 'MULTIPOLYGON EMPTY'::geometry), 3)
FROM corelle.plate_polygon pp
WHERE pp.model_id = rc.model_id
  AND pp.plate_id = rc.plate_id
  AND geom IS null;

CREATE INDEX rotation_cache_geom_idx ON corelle.rotation_cache USING gist (geom);


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

CREATE OR REPLACE FUNCTION corelle_macrostrat.antimeridian_split(
  geom geometry
) RETURNS geometry AS $$
DECLARE
  g1 geometry;
BEGIN
  g1 := ST_WrapX(
    ST_Split(
      ST_MakeValid(ST_ShiftLongitude(g1)),
      -- Antimeridian
      ST_GeomFromText('LINESTRING(180 -90, 180 90)', 4326)
    ),
    180,
    -360
  );
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
DROP FUNCTION IF EXISTS corelle_macrostrat.rotate(geometry, numeric[], boolean);
DROP FUNCTION IF EXISTS corelle_macrostrat.rotated_web_mercator_proj(numeric[]);