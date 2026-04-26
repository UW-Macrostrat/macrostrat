CREATE OR REPLACE VIEW maps.sources_metadata AS
SELECT s.source_id,
  s.slug,
  s.name,
  s.url,
  s.ref_title,
  s.authors,
  s.ref_year,
  s.ref_source,
  s.isbn_doi,
  s.scale,
  s.license,
  s.features,
  s.area,
  s.display_scales,
  s.new_priority AS priority,
  s.status_code,
  s.raster_url,
  s.scale_denominator,
  s.is_finalized,
  s.lines_oriented
FROM maps.sources s
ORDER BY s.source_id DESC;
COMMENT ON VIEW maps.sources_metadata IS 'Convenience view for maps.sources with only metadata fields';

CREATE OR REPLACE VIEW maps.large AS
SELECT polygons_large.map_id,
  polygons_large.orig_id,
  polygons_large.source_id,
  polygons_large.name,
  polygons_large.strat_name,
  polygons_large.age,
  polygons_large.lith,
  polygons_large.descrip,
  polygons_large.comments,
  polygons_large.t_interval,
  polygons_large.b_interval,
  polygons_large.geom
FROM maps.polygons_large;

CREATE OR REPLACE VIEW maps.medium AS
SELECT polygons_medium.map_id,
  polygons_medium.orig_id,
  polygons_medium.source_id,
  polygons_medium.name,
  polygons_medium.strat_name,
  polygons_medium.age,
  polygons_medium.lith,
  polygons_medium.descrip,
  polygons_medium.comments,
  polygons_medium.t_interval,
  polygons_medium.b_interval,
  polygons_medium.geom
FROM maps.polygons_medium;

CREATE OR REPLACE VIEW maps.small AS
SELECT polygons_small.map_id,
  polygons_small.orig_id,
  polygons_small.source_id,
  polygons_small.name,
  polygons_small.strat_name,
  polygons_small.age,
  polygons_small.lith,
  polygons_small.descrip,
  polygons_small.comments,
  polygons_small.t_interval,
  polygons_small.b_interval,
  polygons_small.geom
FROM maps.polygons_small;

CREATE OR REPLACE VIEW maps.tiny AS
SELECT polygons_tiny.map_id,
  polygons_tiny.orig_id,
  polygons_tiny.source_id,
  polygons_tiny.name,
  polygons_tiny.strat_name,
  polygons_tiny.age,
  polygons_tiny.lith,
  polygons_tiny.descrip,
  polygons_tiny.comments,
  polygons_tiny.t_interval,
  polygons_tiny.b_interval,
  polygons_tiny.geom
FROM maps.polygons_tiny;

/** We should probably get rid of this */
CREATE OR REPLACE VIEW maps.vw_legend_with_liths AS
SELECT l.legend_id,
  l.source_id,
  l.name AS map_unit_name,
    array_agg(ll.lith_id) FILTER (WHERE (ll.lith_id IS NOT NULL)) AS lith_ids
FROM (maps.legend l
  LEFT JOIN maps.legend_liths ll ON ((ll.legend_id = l.legend_id)))
GROUP BY l.legend_id, l.source_id, l.name;

GRANT USAGE ON SCHEMA maps TO macrostrat;
GRANT SELECT ON ALL TABLES IN SCHEMA maps TO macrostrat;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA maps TO macrostrat;

