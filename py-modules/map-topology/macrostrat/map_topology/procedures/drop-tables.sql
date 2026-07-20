/* Procedure to delete topology without affecting
mapping data stored in `data_schema`. */

SELECT topology.DropTopoGeometryColumn('map_bounds', 'map_topo', 'topo');
SELECT topology.DropTopology('map_bounds_topology');

DROP SCHEMA IF EXISTS map_bounds CASCADE;
