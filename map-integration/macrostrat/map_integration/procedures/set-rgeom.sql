UPDATE maps.sources
SET rgeom = (
    WITH dump AS (
      SELECT (ST_Dump(geom)).geom
      FROM {primary_table}
      WHERE {where_clause}
    ),
    types AS (
      SELECT ST_GeometryType(geom), geom
      FROM dump
      WHERE ST_GeometryType(geom) = 'ST_Polygon'
    ),
    rings AS (
      SELECT (ST_DumpRings(geom)).geom
      FROM types
    ),
    rings_numbered AS (
      SELECT a.geom, row_number() OVER () AS row_no
      FROM rings a
    ),
    containers AS (
      SELECT ST_Union(a.geom) AS GEOM, b.row_no
      FROM rings_numbered a JOIN rings_numbered b
      ON ST_Intersects(a.geom, b.geom)
      WHERE a.row_no != b.row_no
      GROUP BY b.row_no
    ),
    best AS (
      SELECT ST_Buffer(ST_Union(rings_numbered.geom), 0.0000001) geom
      FROM rings_numbered JOIN containers
      ON containers.row_no = rings_numbered.row_no
      WHERE NOT ST_Covers(containers.geom, rings_numbered.geom)
    )
    SELECT ST_Union(geom) FROM (
    SELECT 'best' as type, geom
    FROM best
    UNION
    SELECT 'next best' as type, geom
    FROM rings_numbered
    ) foo
    WHERE type = (
      CASE
        WHEN (SELECT count(*) FROM best) != NULL
          THEN 'best'
        ELSE 'next best'
        END
    )
)
WHERE source_id = :source_id