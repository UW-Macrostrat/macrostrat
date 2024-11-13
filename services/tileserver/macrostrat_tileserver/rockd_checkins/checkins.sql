CREATE OR REPLACE FUNCTION public.checkins_tile(
  x integer,
  y integer,
  z integer,
  query_params json
) RETURNS bytea AS $$

  WITH tile_loc AS (
    SELECT tile_utils.envelope(x, y, z) envelope
  ),
  -- features in tile envelope
  tile_features AS (
    SELECT
      ST_Transform(geom, 3857) AS geometry,  --using 'geom' from public.checkins
      checkin_id AS id,
      person_id,
      notes,
      rating
    FROM public.checkins
    WHERE ST_Intersects(geom, ST_Transform((SELECT envelope FROM tile_loc), 4326))
  ),
  mvt_features AS (
    SELECT
      id,
      person_id,
      notes,
      rating,
      -- Get the geometry in vector-tile integer coordinates
      ST_AsMVTGeom(geometry, (SELECT envelope FROM tile_loc)) AS geom_downscaled
    FROM tile_features
  ),
  grouped_features AS (
    SELECT
      -- Get cluster expansion zoom level
      tile_utils.cluster_expansion_zoom(ST_Collect(geom_downscaled), 16) AS expansion_zoom,
      geom_downscaled AS geometry,
      count(*) AS n,
      CASE WHEN count(*) < 2 THEN
        string_agg(id::text, ',')
      ELSE
        null
      END AS id,
      CASE WHEN count(*) < 2 THEN
        string_agg(notes, ',')
      ELSE
        null
      END AS notes
    FROM mvt_features
    GROUP BY geom_downscaled
  )
  SELECT ST_AsMVT(grouped_features)
  FROM grouped_features;
$$ LANGUAGE sql IMMUTABLE;

