

    
    
SELECT topology.addtopogeometrycolumn('map_topology', 'columns','columns','topo1','POLYGON');

/* Putting edges into linework*/
INSERT INTO map_digitizer.linework(geometry)
	select ST_Multi(geom) FROM map_topology.edge;
	
/* Putting polygons as buffered centroids into polgon tabel along with macrostrat columnid*/ 
INSERT INTO map_digitizer.polygon(geometry, col_id)
	select ST_Multi(ST_Buffer(ST_Centroid(location), .0001, 2)),
	col_id
from columns.columns;