/* One `maps.lookup` for the four `public.lookup_<scale>` tables.

   The lookup is a cache: every row is derived from a polygon, its legend entry
   and the matches on them, and `make_lookup` rebuilds a source's rows whole. So
   the merge keeps only rows whose polygon still exists (its scale is read off the
   polygon, not off the table the row sat in), clears a `legend_id` whose entry is
   gone, and keeps one row per `map_id`, which lets both references be declared
   valid from the start. The command reports how many rows that leaves behind. */

CREATE TABLE maps.lookup (
    map_id integer PRIMARY KEY
        REFERENCES maps.polygons (map_id) ON DELETE CASCADE,
    scale maps.map_scale NOT NULL,
    legend_id integer
        REFERENCES maps.legend (legend_id) ON DELETE CASCADE,
    unit_ids integer[],
    strat_name_ids integer[],
    concept_ids integer[],
    strat_name_children integer[],
    lith_ids integer[],
    lith_types text[],
    lith_classes text[],
    best_age_top numeric,
    best_age_bottom numeric,
    color character varying(20)
);

INSERT INTO maps.lookup (map_id, scale, legend_id, unit_ids, strat_name_ids,
  concept_ids, strat_name_children, lith_ids, lith_types, lith_classes,
  best_age_top, best_age_bottom, color)
SELECT DISTINCT ON (lk.map_id)
  lk.map_id, p.scale, l.legend_id, lk.unit_ids, lk.strat_name_ids,
  lk.concept_ids, lk.strat_name_children, lk.lith_ids, lk.lith_types, lk.lith_classes,
  lk.best_age_top, lk.best_age_bottom, lk.color
FROM (
  SELECT map_id, legend_id, unit_ids, strat_name_ids, concept_ids, strat_name_children,
    lith_ids, lith_types, lith_classes, best_age_top, best_age_bottom, color
  FROM public.lookup_tiny
  UNION ALL
  SELECT map_id, legend_id, unit_ids, strat_name_ids, concept_ids, strat_name_children,
    lith_ids, lith_types, lith_classes, best_age_top, best_age_bottom, color
  FROM public.lookup_small
  UNION ALL
  SELECT map_id, legend_id, unit_ids, strat_name_ids, concept_ids, strat_name_children,
    lith_ids, lith_types, lith_classes, best_age_top, best_age_bottom, color
  FROM public.lookup_medium
  UNION ALL
  SELECT map_id, legend_id, unit_ids, strat_name_ids, concept_ids, strat_name_children,
    lith_ids, lith_types, lith_classes, best_age_top, best_age_bottom, color
  FROM public.lookup_large
) lk
JOIN maps.polygons p ON p.map_id = lk.map_id
LEFT JOIN maps.legend l ON l.legend_id = lk.legend_id
ORDER BY lk.map_id, lk.legend_id NULLS LAST;

/* No CASCADE: anything still depending on the old tables should stop this and
   be looked at. */
DROP TABLE public.lookup_tiny;
DROP TABLE public.lookup_small;
DROP TABLE public.lookup_medium;
DROP TABLE public.lookup_large;

CREATE INDEX lookup_legend_id_idx ON maps.lookup USING btree (legend_id);
CREATE INDEX lookup_concept_ids_idx ON maps.lookup USING gin (concept_ids);
CREATE INDEX lookup_lith_ids_idx ON maps.lookup USING gin (lith_ids);
CREATE INDEX lookup_strat_name_children_idx ON maps.lookup USING gin (strat_name_children);

/* The old tables as views, their columns in the old order with `scale` appended
   so that an insert naming the table still lands at that scale. */
CREATE VIEW public.lookup_tiny AS
  SELECT map_id, unit_ids, strat_name_ids, lith_ids, best_age_top, best_age_bottom, color,
    lith_types, lith_classes, concept_ids, strat_name_children, legend_id, scale
  FROM maps.lookup WHERE scale = 'tiny' WITH CHECK OPTION;
CREATE VIEW public.lookup_small AS
  SELECT map_id, unit_ids, strat_name_ids, lith_ids, best_age_top, best_age_bottom, color,
    lith_types, lith_classes, concept_ids, strat_name_children, legend_id, scale
  FROM maps.lookup WHERE scale = 'small' WITH CHECK OPTION;
CREATE VIEW public.lookup_medium AS
  SELECT map_id, unit_ids, strat_name_ids, lith_ids, best_age_top, best_age_bottom, color,
    lith_types, lith_classes, concept_ids, strat_name_children, legend_id, scale
  FROM maps.lookup WHERE scale = 'medium' WITH CHECK OPTION;
CREATE VIEW public.lookup_large AS
  SELECT map_id, unit_ids, strat_name_ids, lith_ids, best_age_top, best_age_bottom, color,
    lith_types, lith_classes, concept_ids, strat_name_children, legend_id, scale
  FROM maps.lookup WHERE scale = 'large' WITH CHECK OPTION;
ALTER VIEW public.lookup_tiny ALTER COLUMN scale SET DEFAULT 'tiny';
ALTER VIEW public.lookup_small ALTER COLUMN scale SET DEFAULT 'small';
ALTER VIEW public.lookup_medium ALTER COLUMN scale SET DEFAULT 'medium';
ALTER VIEW public.lookup_large ALTER COLUMN scale SET DEFAULT 'large';
COMMENT ON VIEW public.lookup_tiny IS 'Compatibility view over maps.lookup, which replaced the per-scale lookup tables. New code reads and writes maps.lookup.';
COMMENT ON VIEW public.lookup_small IS 'Compatibility view over maps.lookup, which replaced the per-scale lookup tables. New code reads and writes maps.lookup.';
COMMENT ON VIEW public.lookup_medium IS 'Compatibility view over maps.lookup, which replaced the per-scale lookup tables. New code reads and writes maps.lookup.';
COMMENT ON VIEW public.lookup_large IS 'Compatibility view over maps.lookup, which replaced the per-scale lookup tables. New code reads and writes maps.lookup.';

ANALYZE maps.lookup;
