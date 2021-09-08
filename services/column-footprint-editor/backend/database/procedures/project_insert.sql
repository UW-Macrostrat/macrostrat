WITH A as (
    SELECT id from column_groups WHERE col_group_id = :col_group_id
)
INSERT INTO ${project_schema}.columns(project_id, col_id, col_name, col_group, location) 
    SELECT :project_id, 
            :col_id,
            :col_name,
            id,
            (ST_Dump(ST_GeomFromGeoJSON(:location))).geom
            FROM A;
