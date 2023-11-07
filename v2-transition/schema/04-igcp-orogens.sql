CREATE MATERIALIZED VIEW IF NOT EXISTS corelle_macrostrat.igcp_orogens_index AS
SELECT
	p.id,
	p.color,
	m.id model_id,
	pp.plate_id,
	CASE WHEN ST_Covers(pp.geometry, p.geometry) THEN
		NULL  
	ELSE
		ST_Intersection(pp.geometry, p.geometry)
	END AS geom
FROM sources.igcp_orogens_polygons p
JOIN corelle.plate_polygon pp
  ON ST_Intersects(pp.geometry, p.geometry)
JOIN corelle.model m
  ON m.id = pp.model_id;

CREATE OR REPLACE FUNCTION corelle_macrostrat.igcp_orogens(
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
  tile bytea;
  envelope geometry;
BEGIN
  envelope := ST_TileEnvelope(z, x, y);
  WITH a AS (
  SELECT
    ST_AsMVTGeom(
      ST_Transform(
        corelle_macrostrat.rotate(
          p.geometry, ARRAY[1,0,0,0],
          true
        ), 3857), envelope, 4096, 8, true) AS geometry,
    name,
    t_age,
    b_age,
    interval_id,
    color
  FROM sources.igcp_orogens_polygons p
  WHERE p.geometry && ST_Transform(envelope, 4326)
  )
  SELECT ST_AsMVT(a.*, 'units') FROM a INTO tile;
  RETURN tile;
END;
$$ LANGUAGE plpgsql STABLE PARALLEL SAFE;


CREATE OR REPLACE FUNCTION corelle_macrostrat.igcp_orogens_rotated(
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
  geom geometry;
BEGIN
  SELECT
    ST_AsMVTGeom(geom, ST_TileEnvelope(x, y, z), 4096, 8, true),
    color
  FROM corelle_macrostrat.igcp_orogens_index
  INTO geom;
  RETURN ST_AsMVT(geom, 'burwell', 4096, 'geom');
END;
$$ LANGUAGE plpgsql STABLE PARALLEL SAFE;