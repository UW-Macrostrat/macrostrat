/** Get all sources that are or might be present in a database (even if maps.sources record is absent or malformed) */
WITH correct_sources AS (
	SELECT slug FROM maps.sources
), all_candidates AS (
SELECT slug FROM correct_sources
UNION
SELECT REPLACE(table_name, '_lines', '')
FROM information_schema.tables t
WHERE t.table_schema = 'sources'
  AND t.table_name LIKE '%_lines'
UNION
SELECT REPLACE(table_name, '_polygons', '')
FROM information_schema.tables t
WHERE t.table_schema = 'sources'
  AND t.table_name LIKE '%_polygons'
UNION
SELECT REPLACE(table_name, '_points', '')
FROM information_schema.tables t
WHERE t.table_schema = 'sources'
  AND t.table_name LIKE '%_points'
)
SELECT DISTINCT(slug) slug FROM all_candidates
ORDER BY slug