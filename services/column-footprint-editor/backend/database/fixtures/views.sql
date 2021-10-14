ALTER TABLE ${data_schema}.polygon
	ADD COLUMN col_id integer,
	ADD FOREIGN KEY (col_id) REFERENCES ${project_schema}.columns(id);

CREATE OR REPLACE VIEW ${project_schema}.column_map_face AS
WITH A as(
SELECT c.id,c.project_id, c.col_id, c.col_name, cg.col_group,cg.col_group_id,cg.col_group_name, mtm.geometry from ${topo_schema}.map_face mtm
LEFT JOIN ${data_schema}.polygon mdp
ON ST_Contains(mtm.geometry, mdp.geometry)
LEFT JOIN ${project_schema}.columns c
ON mdp.col_id = c.id
LEFT JOIN ${project_schema}.column_groups cg
ON cg.id = c.col_group
) SELECT A.* from A;