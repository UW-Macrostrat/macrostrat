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

Then, we go through many more updates to clean and simplify the data, and move it into a topologically
correct schema.
See [macrostrat-to-mapboard.sql](macrostrat-to-mapboard.sql) for some of the gory details.
We'll strive to automate this more in the future.

# Run topology watcher

```
mapboard topology provo update --watch
```