-- Add a 'color' column to every column_group table and a 'description' column to every columns table. 
-- Loops through each project schema.
-- Updates the view's for each as well

do $$
DECLARE 
	table_ record;
BEGIN
FOR table_ IN
	SELECT * from pg_tables WHERE tablename LIKE 'column_groups'
LOOP
	RAISE info '%.column_groups',table_.schemaname;
	EXECUTE
	'ALTER TABLE '|| table_.schemaname ||'.column_groups ADD COLUMN color text;'
	'ALTER TABLE '|| table_.schemaname ||'.columns ADD COLUMN description text;'
	'DROP VIEW IF EXISTS ' || table_.schemaname || '.column_map_face;'
	'CREATE VIEW ' || table_.schemaname || '.column_map_face AS
		WITH A as(
		SELECT c.id,c.project_id, c.col_id, c.col_name,c.description, cg.col_group,cg.col_group_id,cg.col_group_name, cg.color, mtm.geometry from ' || table_.schemaname ||'_topology.map_face 				mtm
		LEFT JOIN '|| table_.schemaname ||'_data.polygon mdp
		ON ST_Contains(mtm.geometry, mdp.geometry)
		LEFT JOIN '|| table_.schemaname ||'.columns c
		ON mdp.col_id = c.id
		LEFT JOIN '|| table_.schemaname ||'.column_groups cg
		ON cg.id = c.col_group
		) SELECT A.* from A;'
	USING table_;
END LOOP;
end; $$
;
