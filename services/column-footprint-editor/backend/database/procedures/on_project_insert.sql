INSERT INTO ${data_schema}.polygon(geometry, col_id, type)
	select ST_Multi(ST_Buffer(point, .0001, 2)),
	id,
	'default'
from ${project_schema}.columns;

INSERT INTO ${data_schema}.linework(type, geometry)
SELECT 'default', ST_Multi((ST_Dump(ST_Boundary(location))).geom) from ${project_schema}.columns;

