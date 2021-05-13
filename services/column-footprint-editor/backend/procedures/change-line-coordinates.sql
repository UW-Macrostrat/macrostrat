/*
Updates the existing line, just the geometry
*/
UPDATE map_digitizer.linework
SET geometry = ST_Multi(ST_GeomFromGeoJSON(:geometry_))
WHERE id = :id_;