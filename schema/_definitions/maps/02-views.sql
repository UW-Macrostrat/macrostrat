CREATE OR REPLACE VIEW maps.sources_metadata AS
SELECT
  s.source_id,
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
  s.lines_oriented,
  s.web_geom
FROM maps.sources s
ORDER BY s.source_id DESC;
COMMENT ON VIEW maps.sources_metadata IS 'Convenience view for maps.sources with only metadata fields';

/** The per-scale views. `maps.polygons` was once four tables named `maps.large`
  and so on, then four partitions; these keep the first of those names for v2 and
  the scripts that still read it. */
CREATE OR REPLACE VIEW maps.large AS
SELECT map_id, orig_id, source_id, name, strat_name, age, lith, descrip, comments,
  t_interval, b_interval, geom
FROM maps.polygons WHERE scale = 'large';

CREATE OR REPLACE VIEW maps.medium AS
SELECT map_id, orig_id, source_id, name, strat_name, age, lith, descrip, comments,
  t_interval, b_interval, geom
FROM maps.polygons WHERE scale = 'medium';

CREATE OR REPLACE VIEW maps.small AS
SELECT map_id, orig_id, source_id, name, strat_name, age, lith, descrip, comments,
  t_interval, b_interval, geom
FROM maps.polygons WHERE scale = 'small';

CREATE OR REPLACE VIEW maps.tiny AS
SELECT map_id, orig_id, source_id, name, strat_name, age, lith, descrip, comments,
  t_interval, b_interval, geom
FROM maps.polygons WHERE scale = 'tiny';

/** The former partitions of `maps.polygons` and `maps.lines`, as views.

  Writable: an insert that names one lands in the table with the scale the name
  implies (the column default), and a row of another scale is refused (the check
  option). New code reads and writes the tables themselves.
*/
CREATE OR REPLACE VIEW maps.polygons_large AS
  SELECT * FROM maps.polygons WHERE scale = 'large' WITH CHECK OPTION;
CREATE OR REPLACE VIEW maps.polygons_medium AS
  SELECT * FROM maps.polygons WHERE scale = 'medium' WITH CHECK OPTION;
CREATE OR REPLACE VIEW maps.polygons_small AS
  SELECT * FROM maps.polygons WHERE scale = 'small' WITH CHECK OPTION;
CREATE OR REPLACE VIEW maps.polygons_tiny AS
  SELECT * FROM maps.polygons WHERE scale = 'tiny' WITH CHECK OPTION;
ALTER VIEW maps.polygons_large ALTER COLUMN scale SET DEFAULT 'large';
ALTER VIEW maps.polygons_medium ALTER COLUMN scale SET DEFAULT 'medium';
ALTER VIEW maps.polygons_small ALTER COLUMN scale SET DEFAULT 'small';
ALTER VIEW maps.polygons_tiny ALTER COLUMN scale SET DEFAULT 'tiny';
COMMENT ON VIEW maps.polygons_large IS 'Compatibility view over maps.polygons, which was partitioned by scale. New code reads and writes maps.polygons.';
COMMENT ON VIEW maps.polygons_medium IS 'Compatibility view over maps.polygons, which was partitioned by scale. New code reads and writes maps.polygons.';
COMMENT ON VIEW maps.polygons_small IS 'Compatibility view over maps.polygons, which was partitioned by scale. New code reads and writes maps.polygons.';
COMMENT ON VIEW maps.polygons_tiny IS 'Compatibility view over maps.polygons, which was partitioned by scale. New code reads and writes maps.polygons.';

CREATE OR REPLACE VIEW maps.lines_large AS
  SELECT * FROM maps.lines WHERE scale = 'large' WITH CHECK OPTION;
CREATE OR REPLACE VIEW maps.lines_medium AS
  SELECT * FROM maps.lines WHERE scale = 'medium' WITH CHECK OPTION;
CREATE OR REPLACE VIEW maps.lines_small AS
  SELECT * FROM maps.lines WHERE scale = 'small' WITH CHECK OPTION;
CREATE OR REPLACE VIEW maps.lines_tiny AS
  SELECT * FROM maps.lines WHERE scale = 'tiny' WITH CHECK OPTION;
ALTER VIEW maps.lines_large ALTER COLUMN scale SET DEFAULT 'large';
ALTER VIEW maps.lines_medium ALTER COLUMN scale SET DEFAULT 'medium';
ALTER VIEW maps.lines_small ALTER COLUMN scale SET DEFAULT 'small';
ALTER VIEW maps.lines_tiny ALTER COLUMN scale SET DEFAULT 'tiny';
COMMENT ON VIEW maps.lines_large IS 'Compatibility view over maps.lines, which was partitioned by scale. New code reads and writes maps.lines.';
COMMENT ON VIEW maps.lines_medium IS 'Compatibility view over maps.lines, which was partitioned by scale. New code reads and writes maps.lines.';
COMMENT ON VIEW maps.lines_small IS 'Compatibility view over maps.lines, which was partitioned by scale. New code reads and writes maps.lines.';
COMMENT ON VIEW maps.lines_tiny IS 'Compatibility view over maps.lines, which was partitioned by scale. New code reads and writes maps.lines.';

/** The former `public.lookup_<scale>` tables, as views over `maps.lookup`: the
  old columns in the old order, `scale` and `source_id` appended; `scale` defaults
  so an insert naming the table still lands at that scale. Read by the v2 API and, over `postgres_fdw`, by Rockd.
*/
CREATE OR REPLACE VIEW public.lookup_tiny AS
  SELECT map_id, unit_ids, strat_name_ids, lith_ids, best_age_top, best_age_bottom, color,
    lith_types, lith_classes, concept_ids, strat_name_children, legend_id, scale, source_id
  FROM maps.lookup WHERE scale = 'tiny' WITH CHECK OPTION;
CREATE OR REPLACE VIEW public.lookup_small AS
  SELECT map_id, unit_ids, strat_name_ids, lith_ids, best_age_top, best_age_bottom, color,
    lith_types, lith_classes, concept_ids, strat_name_children, legend_id, scale, source_id
  FROM maps.lookup WHERE scale = 'small' WITH CHECK OPTION;
CREATE OR REPLACE VIEW public.lookup_medium AS
  SELECT map_id, unit_ids, strat_name_ids, lith_ids, best_age_top, best_age_bottom, color,
    lith_types, lith_classes, concept_ids, strat_name_children, legend_id, scale, source_id
  FROM maps.lookup WHERE scale = 'medium' WITH CHECK OPTION;
CREATE OR REPLACE VIEW public.lookup_large AS
  SELECT map_id, unit_ids, strat_name_ids, lith_ids, best_age_top, best_age_bottom, color,
    lith_types, lith_classes, concept_ids, strat_name_children, legend_id, scale, source_id
  FROM maps.lookup WHERE scale = 'large' WITH CHECK OPTION;
ALTER VIEW public.lookup_tiny ALTER COLUMN scale SET DEFAULT 'tiny';
ALTER VIEW public.lookup_small ALTER COLUMN scale SET DEFAULT 'small';
ALTER VIEW public.lookup_medium ALTER COLUMN scale SET DEFAULT 'medium';
ALTER VIEW public.lookup_large ALTER COLUMN scale SET DEFAULT 'large';
COMMENT ON VIEW public.lookup_tiny IS 'Compatibility view over maps.lookup, which replaced the per-scale lookup tables. New code reads and writes maps.lookup.';
COMMENT ON VIEW public.lookup_small IS 'Compatibility view over maps.lookup, which replaced the per-scale lookup tables. New code reads and writes maps.lookup.';
COMMENT ON VIEW public.lookup_medium IS 'Compatibility view over maps.lookup, which replaced the per-scale lookup tables. New code reads and writes maps.lookup.';
COMMENT ON VIEW public.lookup_large IS 'Compatibility view over maps.lookup, which replaced the per-scale lookup tables. New code reads and writes maps.lookup.';

/** We should probably get rid of this */
CREATE OR REPLACE VIEW maps.vw_legend_with_liths AS
SELECT l.legend_id,
  l.source_id,
  l.name AS map_unit_name,
    array_agg(ll.lith_id) FILTER (WHERE (ll.lith_id IS NOT NULL)) AS lith_ids
FROM (maps.legend l
  LEFT JOIN maps.legend_liths ll ON ((ll.legend_id = l.legend_id)))
GROUP BY l.legend_id, l.source_id, l.name;


