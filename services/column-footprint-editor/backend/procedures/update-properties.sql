/*
SQL statement for changing 
*/
UPDATE ${project_schema}.columns
SET col_name = :column_name,
    col_group = :group
WHERE id = :id;