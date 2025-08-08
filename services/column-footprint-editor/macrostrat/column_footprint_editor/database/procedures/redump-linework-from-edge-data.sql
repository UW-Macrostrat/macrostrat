TRUNCATE {data_schema}.linework CASCADE;

ALTER SEQUENCE {data_schema}.linework_id_seq RESTART WITH 1;

INSERT INTO {data_schema}.linework(type, geometry)
SELECT 'default', ST_Multi(geom) from {topo_schema}.edge_data;
