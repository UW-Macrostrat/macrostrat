


-- TRUNCATE map_digitizer.linework CASCADE;

-- /*Create topolgy column and add geom column to topology*/
-- SELECT topology.addtopogeometrycolumn('map_topology', 'columns','columns','topo','POLYGON');

-- INSERT INTO columns.columns (topo)
-- 	SELECT topology.totopogeom(location, 'map_topology', 3) from columns.columns;

-- INSERT INTO map_digitizer.linework(type, geometry)
-- 	select 'default', ST_Multi(geom) FROM map_topology.edge;
    
SELECT topology.addtopogeometrycolumn('${topo_schema}', '${project_schema}','columns','topo1','POLYGON');

/* Putting edges into linework*/
INSERT INTO ${data_schema}.linework(geometry)
	select ST_Multi(geom) FROM ${topo_schema}.edge;
	
/* Putting polygons as buffered centroids into polgon tabel along with macrostrat columnid*/ 
INSERT INTO ${data_schema}.polygon(geometry, col_id)
	select ST_Multi(ST_Buffer(ST_PointOnSurface(ST_MakeValid(location)), .0001, 2)),
	id
from ${project_schema}.columns;