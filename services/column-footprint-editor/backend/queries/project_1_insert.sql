/*
This will be a parameterized INSERT statement into the column table of the db.
*/
INSERT INTO columns.columns(project_id, col_id, col_name, col_group, location) VALUES (
    :project_id, :col_id, :col_name, :col_group, ST_GeomFromGeoJSON(:location))