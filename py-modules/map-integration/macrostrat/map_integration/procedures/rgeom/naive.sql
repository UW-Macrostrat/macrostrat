WITH res AS (
  SELECT source_id,
    ST_Transform(ST_Union(ST_MakeValid(ST_Transform({geom_column}, :srid))), 4326) AS geometry
  FROM {primary_table}
  WHERE {where_clause}
  GROUP BY source_id
)
UPDATE maps.sources
SET rgeom = res.geometry
FROM res
WHERE sources.source_id = res.source_id
