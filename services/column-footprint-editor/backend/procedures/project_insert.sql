INSERT INTO ${project_schema}.columns(project_id, col_id, col_name, col_group, location) VALUES (
    :project_id, :col_id, :col_name, :col_group, (ST_Dump(ST_GeomFromGeoJSON(:location))).geom);
