
SELECT id, col_group_id, project_id, status_code, col_position, col, col_name, lat, lng, col_area, ST_AsText(coordinate) AS wkt, created
FROM cols

