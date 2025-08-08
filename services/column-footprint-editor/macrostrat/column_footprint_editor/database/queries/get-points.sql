SELECT
    ST_AsGeoJSON(geometry) point,
    id,
    project_id,
    col_id,
    col_name,
    description,
    col_group_id,
    col_group,
    col_group_name,
    color
from {project_schema}.column_map_face c;
