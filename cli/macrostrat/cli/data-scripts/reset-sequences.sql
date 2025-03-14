/**
Reset the map_id sequence to its current maximum value.
*/
SELECT pg_catalog.setval('maps.map_ids', (SELECT MAX(map_id) FROM maps.polygons));
