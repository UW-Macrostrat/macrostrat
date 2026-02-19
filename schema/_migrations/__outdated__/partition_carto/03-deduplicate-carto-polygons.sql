/**
Date: 2023-10-01
For some reason, we've got a lot of duplicated map_id entries in our carto
tables. It would be better to have a unique constraint on map_id, but we can't
do that until we've removed the duplicates.
*/

ALTER TABLE carto.polygons ADD COLUMN updated boolean NOT NULL DEFAULT false;
ALTER TABLE carto.polygons_tiny ADD COLUMN updated boolean NOT NULL DEFAULT false;
ALTER TABLE carto.polygons_small ADD COLUMN updated boolean NOT NULL DEFAULT false;
ALTER TABLE carto.polygons_medium ADD COLUMN updated boolean NOT NULL DEFAULT false;
ALTER TABLE carto.polygons_large ADD COLUMN updated boolean NOT NULL DEFAULT false;

INSERT INTO carto.polygons_tiny (map_id, source_id, geom_scale, geom, scale, updated)
SELECT
  map_id,
  source_id,
  geom_scale,
  ST_Union(geom),
  scale,
  true
FROM carto.polygons_tiny
GROUP BY (map_id, source_id, geom_scale, scale)
HAVING count(map_id) > 1;

DELETE FROM carto.polygons_tiny WHERE NOT updated AND map_id IN (SELECT map_id FROM carto.polygons_tiny WHERE updated);

INSERT INTO carto.polygons_small (map_id, source_id, geom_scale, geom, scale, updated)
SELECT
  map_id,
  source_id,
  geom_scale,
  ST_Union(geom),
  scale,
  true
FROM carto.polygons_small
GROUP BY (map_id, source_id, geom_scale, scale)
HAVING count(map_id) > 1;

DELETE FROM carto.polygons_small WHERE NOT updated AND map_id IN (SELECT map_id FROM carto.polygons_small WHERE updated);

INSERT INTO carto.polygons_medium (map_id, source_id, geom_scale, geom, scale, updated)
SELECT
  map_id,
  source_id,
  geom_scale,
  ST_Union(geom),
  scale,
  true
FROM carto.polygons_medium
GROUP BY (map_id, source_id, geom_scale, scale)
HAVING count(map_id) > 1;

DELETE FROM carto.polygons_medium WHERE NOT updated AND map_id IN (SELECT map_id FROM carto.polygons_medium WHERE updated);

INSERT INTO carto.polygons_large (map_id, source_id, geom_scale, geom, scale, updated)
SELECT
  map_id,
  source_id,
  geom_scale,
  ST_Union(geom),
  scale,
  true
FROM carto.polygons_large
GROUP BY (map_id, source_id, geom_scale, scale)
HAVING count(map_id) > 1;

DELETE FROM carto.polygons_tiny WHERE NOT updated AND map_id IN (SELECT map_id FROM carto.polygons_tiny WHERE updated);
DELETE FROM carto.polygons_small WHERE NOT updated AND map_id IN (SELECT map_id FROM carto.polygons_small WHERE updated);
DELETE FROM carto.polygons_medium WHERE NOT updated AND map_id IN (SELECT map_id FROM carto.polygons_medium WHERE updated);
DELETE FROM carto.polygons_large WHERE NOT updated AND map_id IN (SELECT map_id FROM carto.polygons_large WHERE updated);

ALTER TABLE carto.polygons_tiny DROP COLUMN updated;
ALTER TABLE carto.polygons_small DROP COLUMN updated;
ALTER TABLE carto.polygons_medium DROP COLUMN updated;
ALTER TABLE carto.polygons_large DROP COLUMN updated;
ALTER TABLE carto.polygons DROP COLUMN updated;
