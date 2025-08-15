WITH A as (
    SELECT id from {project_schema}.column_groups WHERE col_group_id = :col_group_id
)
INSERT INTO {project_schema}.columns(project_id, col_id, col_name, col_group, point)
    SELECT :project_id,
            :col_id,
            :col_name,
            id,
            (ST_Dump(ST_GeomFromGeoJSON(:point))).geom
            FROM A;
