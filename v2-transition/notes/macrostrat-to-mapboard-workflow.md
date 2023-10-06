Export from Macrostrat database

```sql
CREATE SCHEMA provo_export;

CREATE TABLE provo_export.polgyons AS
SELECT * FROM maps.large
WHERE source_id = 61;

CREATE TABLE provo_export.lines AS
SELECT * FROM lines.large
WHERE source_id = 61;

CREATE TABLE provo_export.legend AS
SELECT * FROM maps.legend
WHERE source_id = 61;

CREATE TABLE provo_export.map_legend AS
SELECT
ml.map_id,
ml.legend_id
FROM maps.map_legend ml
JOIN maps.large m
  ON m.map_id = ml.map_id
 AND m.source_id = 61;
CREATE TABLE provo_export.meta AS
SELECT * FROM maps.sources
WHERE source_id = 61;

CREATE TABLE provo_export.points AS
SELECT * FROM points.points
WHERE source_id = 61;
```

## Dump PostGIS database

```
docker compose exec database pg_dump -Fc --schema=provo_export macrostrat > provo.pg-dump
```

## Create a new Mapboard project

```
mapboard create --srid 26912 provo
```


## Import into Mapboard

```
cat provo.pg-dump | mapboard compose exec -T db pg_restore -U mapboard_admin provo
```

### Update SRIDs

```sql
ALTER TABLE provo_export.polgyons
ALTER COLUMN geom TYPE geometry(MultiPolygon, 26912)
USING ST_Transform(geom, 26912);

ALTER TABLE provo_export.lines
ALTER COLUMN geom TYPE geometry(MultiLineString, 26912)
USING ST_Transform(geom, 26912);

ALTER TABLE provo_export.points
ALTER COLUMN geom TYPE geometry(Point, 26912)
USING ST_Transform(geom, 26912);
```

```sql
--- PL/PGSQL function to build a large representative blob near the center of a polygon
CREATE OR REPLACE FUNCTION map_topology.build_polygon_seed(polygon geometry)
RETURNS geometry AS
$$
DECLARE
  centroid geometry;
  blob geometry;
  factor double precision;
BEGIN
  centroid := ST_Centroid(polygon);
  FOR i IN 1..10 LOOP
    factor := 100 / pow(i, 2);
    blob := ST_Buffer(centroid, factor);
    blob := ST_Intersection(blob, ST_Buffer(polygon, -factor/2);
    IF ST_Area(blob) > 0.01 THEN
      EXIT;
    END IF;
  END LOOP;
  RETURN blob;
END;
LANGUAGE plpgsql;
```

...lots more updates

# Run topology watcher

```
mapboard topology provo update --watch
```