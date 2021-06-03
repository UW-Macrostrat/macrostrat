CREATE OR REPLACE VIEW columns.column_map_face AS
WITH A as(
SELECT c.id,c.project_id, c.col_id, c.col_name, c.col_group, mtm.geometry from map_topology.map_face mtm
LEFT JOIN map_digitizer.polygon mdp
ON ST_Contains(mtm.geometry, mdp.geometry)
LEFT JOIN columns.columns c
ON mdp.col_id = c.id
) SELECT A.*, '#F95E5E' col_color from A
WHERE A.col_id IS NULL
UNION 
SELECT A.*,'#0BDCB9' col_color from A
WHERE A.col_id IS NOT NULL
;