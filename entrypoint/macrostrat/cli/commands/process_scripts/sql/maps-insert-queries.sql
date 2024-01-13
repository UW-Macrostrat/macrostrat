WITH lines AS (
SELECT
	line_id
FROM lines.tiny
UNION ALL
SELECT
	line_id
FROM lines.small
UNION ALL
SELECT
	line_id
FROM lines.medium
UNION ALL
SELECT
	line_id
FROM lines.large)
SELECT max(line_id)+1 FROM lines;

ALTER SEQUENCE line_ids RESTART WITH 1972446;


INSERT INTO lines.medium (
	orig_id,
	source_id,
	name,
	new_type,
	new_direction,
	descrip,
	geom
)
SELECT 
	orig_id,
	source_id,
	name,
	type,
	direction,
	descrip,
	geom
FROM sources.ca_death_valley_gwat_linestrings
WHERE coalesce(ready, true);

/* Map polygons */
INSERT INTO maps.medium (
	orig_id,
	source_id,
	name,
	strat_name,
	age,
	lith,
	descrip,
	comments,
	t_interval,
	b_interval,
	geom
)
SELECT
	orig_id,
	source_id,
	name,
	strat_name,
	age,
	lith,
	descrip,
	comments,
	t_interval,
	b_interval,
	geom
FROM sources.ca_death_valley_gwat_polygons
WHERE coalesce(ready, true);