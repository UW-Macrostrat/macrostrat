SELECT ST_AsGeoJSON(geometry) polygon, id, project_id, col_id, col_name, col_group, col_color from columns.column_map_face c;
