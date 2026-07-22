/** Delete legend entries for maps that are not referenced in the sources table. */
WITH a AS (
  SELECT legend_id, source_id
  FROM maps.legend
  WHERE source_id NOT IN (SELECT source_id FROM maps.sources)
),
  d1 AS (
    DELETE FROM maps.map_legend WHERE legend_id IN (SELECT legend_id FROM a)
  )
DELETE FROM maps.legend WHERE legend_id IN (SELECT legend_id FROM a);
