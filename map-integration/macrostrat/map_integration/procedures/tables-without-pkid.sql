/** Here, we get all tables that don't yet have
a primary key column. */
SELECT
  source_id,
	slug,
	table_name,
	coalesce(c.table_name = s.primary_table, false) is_polygon,
	coalesce(c.table_name = s.primary_line_table, false) is_line
FROM information_schema.tables c
JOIN maps.sources s
  ON c.table_name IN (s.primary_table, s.primary_line_table)
WHERE table_schema = 'sources'
  AND NOT EXISTS (
    -- no _pkid column
    SELECT 1
    FROM information_schema.columns c2
    WHERE c2.table_schema = 'sources'
      AND c2.table_name = c.table_name
      AND c2.column_name = '_pkid'
  )