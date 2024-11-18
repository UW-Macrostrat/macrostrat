WITH tile AS (
  SELECT
    ST_TileEnvelope(:z, :x, :y) AS envelope
), checkins AS (SELECT person_id,
                       notes,
                       rating,
                       ST_AsMVTGeom(ST_Transform(ST_SetSRID(geom,4326), 3857), tile.envelope)
                FROM public.checkins,
                     tile
                WHERE geom IS NOT NULL
                  AND ST_Intersects(ST_SetSRID(geom, 4326), ST_Transform(tile.envelope, 4326)))
 SELECT ST_AsMVT(checkins, 'default') FROM checkins