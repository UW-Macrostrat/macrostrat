SELECT x.line_id, x.source_id, COALESCE(q.descrip, '') AS descrip, COALESCE(q.name, '') AS name, COALESCE(q.new_direction, '') AS direction, COALESCE(q.new_type, '') AS type, x.geom
FROM carto_new.lines_small x
LEFT JOIN (
   SELECT * FROM lines.tiny
   UNION ALL
   SELECT * FROM lines.small
) q on q.line_id = x.line_id
LEFT JOIN maps.sources ON x.source_id = sources.source_id
WHERE sources.status_code = 'active'
