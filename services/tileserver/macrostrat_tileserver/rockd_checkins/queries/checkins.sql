WITH tile AS (
  SELECT
    ST_TileEnvelope(:z, :x, :y) AS envelope
), checkins AS (
  SELECT
    checkin_id id,
    person_id person,
    photo,
    notes,
    rating,
    date_part('year', coalesce(updated, created)) AS year,
    ST_AsMVTGeom(ST_Transform(ST_SetSRID(geom,4326), 3857), tile.envelope)
  FROM public.checkins,
       tile
  WHERE geom IS NOT NULL
    AND status = 1 -- Only public checkins that haven't been flagged
    AND ST_Intersects(
    ST_SetSRID(geom, 4326),
    ST_Transform(tile.envelope, 4326)
    )
)
SELECT ST_AsMVT(checkins, 'default') FROM checkins
