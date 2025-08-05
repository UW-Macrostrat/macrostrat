DROP SCHEMA ${data_schema} CASCADE;
DROP SCHEMA ${project_schema} CASCADE;

DELETE FROM projects WHERE project_id = :project_id;
