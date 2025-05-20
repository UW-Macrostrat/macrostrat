SELECT x.line_id, x.source_id, COALESCE(q.descrip, '') AS descrip, COALESCE(q.name, '') AS name, COALESCE(q.new_direction, '') AS direction, COALESCE(q.new_type, '') AS type, x.geom
FROM carto_new.lines_tiny x
LEFT JOIN lines.tiny q on q.line_id = x.line_id
