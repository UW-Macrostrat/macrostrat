/*
SQL to truncate tables and remove topology, 
for min product where we can only have one project at a time
*/

SET session_replication_role = replica;

UPDATE map_digitizer.linework
SET
  topo = null,
  geometry_hash = null,
  topology_error = null;

TRUNCATE TABLE map_topology.face CASCADE;
TRUNCATE TABLE map_topology.relation CASCADE;
TRUNCATE TABLE map_topology.map_face CASCADE;

INSERT INTO map_topology.face (face_id) VALUES (0);

ALTER SEQUENCE map_topology.node_node_id_seq RESTART WITH 1;
ALTER SEQUENCE map_topology.face_face_id_seq RESTART WITH 1;
ALTER SEQUENCE map_topology.edge_data_edge_id_seq RESTART WITH 1;
ALTER SEQUENCE map_topology.topogeo_s_1 RESTART WITH 1;

SELECT setval(pg_get_serial_sequence('map_topology.map_face', 'id'), coalesce(max(id),0)+1, false)
  FROM map_topology.map_face;
SET session_replication_role = DEFAULT;

TRUNCATE map_topology.map_face CASCADE;

ALTER SEQUENCE map_topology.map_face_id_seq RESTART WITH 1;


TRUNCATE map_digitizer.linework CASCADE;
TRUNCATE columns.columns CASCADE;
TRUNCATE map_digitizer.polygon CASCADE;

ALTER SEQUENCE map_digitizer.linework_id_seq RESTART WITH 1;
ALTER SEQUENCE columns.columns_id_seq RESTART WITH 1;
ALTER SEQUENCE map_digitizer.polygon_id_seq RESTART WITH 1;

