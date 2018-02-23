SELECT z.map_id, z.source_id, COALESCE(m.name, '') AS name, COALESCE(m.age, '') AS age, COALESCE(m.lith, '') AS lith, COALESCE(m.descrip, '') AS descrip, COALESCE(m.comments, '') AS comments, m.t_interval AS t_int_id, ta.interval_name AS t_int, l.best_age_top::numeric AS best_age_top, m.b_interval AS b_int_id, tb.interval_name AS b_int, l.best_age_bottom::numeric AS best_age_bottom, COALESCE(l.color, '#777777') AS color, z.geom
FROM carto_new.large z
LEFT JOIN (
  SELECT * FROM maps.large
  UNION ALL
  SELECT * FROM maps.medium
) m ON z.map_id = m.map_id
LEFT JOIN (
  SELECT * FROM lookup_large
  UNION ALL
  SELECT * FROM lookup_medium
) l ON z.map_id = l.map_id
LEFT JOIN macrostrat.intervals ta ON ta.id = m.t_interval LEFT JOIN macrostrat.intervals tb ON tb.id = m.b_interval;
