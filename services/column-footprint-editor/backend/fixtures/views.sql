CREATE OR REPLACE VIEW ${project_schema}.column_map_face AS
WITH A as(
SELECT c.id,c.project_id, c.col_id, c.col_name, c.col_group, mtm.geometry from ${topo_schema}.map_face mtm
LEFT JOIN ${data_schema}.polygon mdp
ON ST_Contains(mtm.geometry, mdp.geometry)
LEFT JOIN ${project_schema}.columns c
ON mdp.col_id = c.id
) SELECT A.*, '#F95E5E' col_color from A
WHERE A.col_id IS NULL
UNION 
SELECT A.*,'#0BDCB9' col_color from A
WHERE A.col_id IS NOT NULL
;