/*
SQL statement for changing 
*/
WITH A AS(
    SELECT id, :col_name "col_name" FROM ${project_schema}.column_groups WHERE id = :col_group_id
)
UPDATE ${project_schema}.columns c
SET col_name = A.col_name,
    col_group = A.id,
    description = :description
FROM A
WHERE c.id = :id;