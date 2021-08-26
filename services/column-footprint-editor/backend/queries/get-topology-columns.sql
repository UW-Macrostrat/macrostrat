SELECT ST_AsGeoJSON(geometry) polygon, id, project_id, col_id, col_name, col_group_id, col_group, col_group_name, col_color from ${project_schema}.column_map_face c;
