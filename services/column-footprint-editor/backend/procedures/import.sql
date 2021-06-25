/*
SQL to be run on the import of a new project from macrostrat
*/

/* Putting polygons as buffered centroids into polgon tabel along with macrostrat column_id*/ 
INSERT INTO map_digitizer.polygon(geometry, col_id, type)
	select ST_Multi(ST_Buffer(ST_PointOnSurface(ST_MakeValid(location)), .0001, 2)),
	id,
	'default'
from columns.columns;

INSERT INTO map_digitizer.linework(type, geometry)
SELECT 'default', ST_Multi((ST_Dump(ST_Boundary(location))).geom) from columns.columns;

-- TRUNCATE map_digitizer.linework CASCADE;

-- /*Create topolgy column and add geom column to topology*/
-- SELECT topology.addtopogeometrycolumn('map_topology', 'columns','columns','topo','POLYGON');

-- INSERT INTO columns.columns (topo)
-- 	SELECT topology.totopogeom(location, 'map_topology', 3) from columns.columns;

-- INSERT INTO map_digitizer.linework(type, geometry)
-- 	select 'default', ST_Multi(geom) FROM map_topology.edge;
