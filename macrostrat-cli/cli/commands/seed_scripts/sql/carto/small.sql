SELECT z.map_id, z.source_id, l.legend_id, l.best_age_top::numeric AS best_age_top, l.best_age_bottom::numeric AS best_age_bottom, COALESCE(l.color, '#777777') AS color, COALESCE(l.name, '') AS name, COALESCE(l.age, '') AS age, COALESCE(l.lith, '') AS lith, COALESCE(l.descrip, '') AS descrip, COALESCE(l.comments, '') AS comments, l.t_interval AS t_int_id, COALESCE(ta.interval_name, '') AS t_int, l.b_interval AS b_int_id, tb.interval_name AS b_int, COALESCE(sources.url, '') AS ref_url, COALESCE(sources.name, '') AS ref_name, COALESCE(sources.ref_title, '') AS ref_title, COALESCE(sources.authors, '') AS ref_authors, COALESCE(sources.ref_source, '') AS ref_source, COALESCE(sources.ref_year, '') AS ref_year, COALESCE(sources.isbn_doi, '') AS ref_isbn, z.geom
FROM carto_new.small z
LEFT JOIN maps.map_legend ON z.map_id = map_legend.map_id
LEFT JOIN maps.legend AS l ON l.legend_id = map_legend.legend_id
LEFT JOIN macrostrat.intervals ta ON ta.id = l.t_interval LEFT JOIN macrostrat.intervals tb ON tb.id = l.b_interval
LEFT JOIN maps.sources ON l.source_id = sources.source_id
WHERE sources.status_code = 'active'
AND ST_Intersects(z.geom, ST_GeomFromText( 
