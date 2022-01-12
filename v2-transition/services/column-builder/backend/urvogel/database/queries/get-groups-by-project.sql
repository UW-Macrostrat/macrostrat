SELECT DISTINCT cg.* from macrostrat.col_groups cg
LEFT JOIN macrostrat.cols c
ON c.col_group_id = cg.id
LEFT JOIN macrostrat.projects p
ON c.project_id = p.id
WHERE p.id = %(project_id)s;