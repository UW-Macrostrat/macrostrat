WITH B as (
INSERT INTO {project_schema}.columns(project_id, col_id, col_name, col_group,location, description)
    values (:project_id,
            :col_id,
            :col_name,
            :col_group_id,
            (ST_Dump(ST_GeomFromGeoJSON(:location))).geom,
            :description)
    RETURNING id
)
INSERT INTO {data_schema}.polygon(geometry, col_id, type)
	select ST_Multi(ST_Buffer(ST_PointOnSurface(ST_MakeValid(:location)), .0001, 2)),
	B.id,
	'default'
from B
RETURNING id;
