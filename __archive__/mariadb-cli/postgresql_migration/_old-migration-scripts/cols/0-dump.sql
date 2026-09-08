
SELECT 
c.id, 
col_group_id, 
project_id, 
col_type, 
status_code, 
col_position, 
col, 
col_name, 
lat, 
lng, 
col_area, 
ST_AsText(coordinate) AS wkt, 
created,
cn.notes
FROM cols c 
LEFT JOIN col_notes cn
ON c.id = cn.col_id
