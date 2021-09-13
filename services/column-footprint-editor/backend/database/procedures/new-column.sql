WITH B as (WITH A as (
    SELECT id from ${project_schema}.column_groups WHERE col_group_id = :col_group_id
)
INSERT INTO ${project_schema}.columns(project_id, col_id, col_name, col_group, location) 
    SELECT :project_id, 
            :col_id,
            :col_name,
            A.id,
            (ST_Dump(ST_GeomFromGeoJSON(:location))).geom
            FROM A
    RETURNING id
)
INSERT INTO ${data_schema}.polygon(geometry, col_id, type)
	select ST_Multi(ST_Buffer(ST_PointOnSurface(ST_MakeValid(:location)), .0001, 2)),
	B.id,
	'default'
from B
RETURNING id;