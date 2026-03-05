# this SQL must be executed on macrostrat before macrostrat_import_2.5.py can be successfully run

DROP VIEW macrostrat_api.col_ref_expanded;
DROP VIEW macrostrat_api.col_sections;
ALTER TABLE macrostrat.cols ALTER COLUMN col_name TYPE character varying;

CREATE VIEW macrostrat_api.col_sections AS  SELECT c.id AS col_id,
    c.col_name,
    u.section_id,
    u.position_top,
    u.position_bottom,
    fo.interval_name AS bottom,
    lo.interval_name AS top
   FROM macrostrat.cols c
     LEFT JOIN macrostrat.units u ON u.col_id = c.id
     LEFT JOIN macrostrat.intervals fo ON u.fo = fo.id
     LEFT JOIN macrostrat.intervals lo ON u.lo = lo.id;
     
CREATE VIEW macrostrat_api.col_ref_expanded AS  SELECT c.id AS col_id,
    c.col_name,
    c.col AS col_number,
    ''::text AS notes,
    c.lat,
    c.lng,
    json_build_object('id', r.id, 'pub_year', r.pub_year, 'author', r.author, 'ref', r.ref, 'doi', r.doi, 'url', r.url) AS ref
   FROM macrostrat.cols c
     LEFT JOIN macrostrat.col_refs cr ON c.id = cr.col_id
     LEFT JOIN macrostrat.refs r ON cr.ref_id = r.id;
