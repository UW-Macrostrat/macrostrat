WITH a AS (
	SELECT
    req_id,
		layer,
		ext,
		x,
		y,
		z,
		substring(nullif(referrer, '') from '(?:.*://)?(?:www\.)?([^(/:)?]*)') referrer,
		app,
		app_version,
		date_trunc('day', time) date
	FROM requests
  WHERE req_id > (SELECT last_row_id FROM stats.processing_status)
	ORDER BY req_id
	LIMIT 100000
),
b AS (
  INSERT INTO stats.day_index (layer, ext, referrer, app, app_version, date, num_requests)
	SELECT
    layer,
    ext,
    referrer,
    app,
    app_version,
    date,
    count(*)
  FROM a
	GROUP BY layer, ext, app, referrer, app_version, date
  ON CONFLICT (layer, ext, referrer, app, app_version, date)
  DO UPDATE SET
    num_requests = stats.day_index.num_requests + EXCLUDED.num_requests
  RETURNING *
),
reduced_complexity_locations AS (
	SELECT
    layer,
    ext,
    CASE WHEN z > 8 THEN
      x >> (z - 8) -- Bit shift right by the difference between the current zoom level and 8 
    ELSE x END x,
    CASE WHEN z > 8 THEN
      y >> (z - 8)
    ELSE y END y,
    CASE WHEN z > 8 THEN 8 ELSE z END z,
    z orig_z
	FROM a
),
c AS (
  INSERT INTO stats.location_index (layer, ext, x, y, z, orig_z, num_requests)
  SELECT
    layer,
    ext,
    x,
    y,
    z,
    orig_z,
    count(*) num_requests
  FROM reduced_complexity_locations
  GROUP BY layer, ext, x, y, z, orig_z
  ON CONFLICT (layer, ext, x, y, z, orig_z)
  DO UPDATE SET
    num_requests = stats.location_index.num_requests + EXCLUDED.num_requests
),
max_row AS (
  SELECT max(req_id) id FROM a
),
d AS (
  UPDATE stats.processing_status
  SET last_row_id = id
  FROM max_row
  WHERE id IS NOT NULL
)
SELECT max(req_id) last_row_id, count(*) n_rows FROM a;
