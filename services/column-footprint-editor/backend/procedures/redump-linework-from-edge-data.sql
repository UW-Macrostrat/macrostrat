/*
SQL file to redump lines to the linkwork table from the topology.edge_data
*/

TRUNCATE map_digitizer.linework CASCADE;

ALTER SEQUENCE map_digitizer.linework_id_seq RESTART WITH 1;

INSERT INTO map_digitizer.linework(type, geometry)
SELECT 'default', ST_Multi(geom) from map_topology.edge_data;