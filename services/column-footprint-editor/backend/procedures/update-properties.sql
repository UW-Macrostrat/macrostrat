/*
SQL statement for changing 
*/
UPDATE columns.columns
SET col_name = :column_name,
    col_group = :group
WHERE id = :id;