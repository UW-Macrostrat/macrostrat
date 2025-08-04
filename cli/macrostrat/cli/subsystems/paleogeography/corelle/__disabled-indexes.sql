-- Adjust layers to have simplified geometries for rapid filtering
-- This should maybe be moved to Corelle
ALTER TABLE corelle.plate_polygon ADD COLUMN geom_simple geometry(Geometry, 4326);
ALTER TABLE corelle.rotation_cache ADD COLUMN geom geometry(Geometry, 4326);

UPDATE corelle.plate_polygon
SET geom_simple = corelle_macrostrat.antimeridian_split(ST_Multi(ST_Simplify(ST_Buffer(geometry, 0.1), 0.1)))
WHERE geom_simple IS NULL;

/** This isn't properly a "schema update". It is a required cache-filling operation. But it isn't
    necessarily correct practice to run it every time the schema is regenerated. */
UPDATE corelle.rotation_cache rc SET
  geom = corelle_macrostrat.rotate(geom_simple, rotation, true)
FROM corelle.plate_polygon pp
WHERE pp.model_id = rc.model_id
  AND pp.plate_id = rc.plate_id
  AND geom IS null;

CREATE INDEX rotation_cache_geom_idx ON corelle.rotation_cache USING gist (geom);