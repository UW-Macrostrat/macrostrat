/* The map units at a location, resolved through the compilation system.

   `map_bounds.units_at` is the one entry point: it applies the multiscale hop
   (`carto` at zoom 5 is `carto-small`), resolves a compilation with faces in
   two indexed phases (its `map_face` coverage, then one lookup per face for
   that map's content), answers a plain map or a mosaic member through
   `polygons_of`, and reads `sys:carto-legacy` from the materialized `carto.*`
   build. It is called once, with constant arguments, and returns keys only.

   Everything below decorates those keys -- the polygon's own text, the legend
   entry, interval names -- and runs against at most `:limit` rows, ordered by
   rank within the compilation first. Legend fields are coalesced over the
   polygon's own columns: a polygon whose map has no legend entry still names
   itself. `map_id` and `orig_id` are there so a client can go to the polygon
   for the source map's unedited text. */
WITH units AS (
  SELECT
    u.map_id,
    u.source_id,
    u.scale,
    u.map_layer_id,
    u.map_face_id,
    u.member_id,
    u.priority_path
  FROM map_bounds.units_at(
    CAST(:ident AS text),
    ST_SetSRID(ST_GeomFromText(:bounds), 4326),
    CAST(:zoom AS integer)
  ) u
  ORDER BY u.priority_path DESC NULLS LAST, u.map_id
  LIMIT :limit
)
SELECT
  -- A layer is named by its compilation.
  mls.slug AS map_layer,
  u.map_layer_id,
  u.map_face_id,
  p.map_id,
  p.orig_id,
  p.scale,
  u.source_id,
  s.slug AS source_slug,
  s.name AS source_name,
  /* Rank within the compilation, as the path of priorities taken on the way
     down to this map. Null outside a compilation with faces. */
  array_to_string(u.priority_path, '.') AS priority,
  coalesce(u.priority_path, '{}') AS priority_path,
  /* The member of the compilation this map belongs to, skipping the scale
     layers -- from `carto-large` British Columbia is `bc-surface`. */
  u.member_id,
  v.slug AS member_slug,
  v.name AS member_name,
  l.legend_id,
  coalesce(l.name, p.name) AS map_unit_name,
  coalesce(l.strat_name, p.strat_name) AS strat_name,
  coalesce(l.age, p.age) AS age,
  coalesce(l.lith, p.lith) AS lith,
  coalesce(l.descrip, p.descrip) AS descrip,
  coalesce(l.comments, p.comments) AS comments,
  l.best_age_top::float AS t_age,
  l.best_age_bottom::float AS b_age,
  coalesce(l.t_interval, p.t_interval) AS t_interval,
  /* Joined on each candidate separately rather than on a `coalesce` of the two:
     a coalesce in the join condition is not an indexable key, and the interval
     table then gets rescanned per row. */
  coalesce(lti.interval_name, pti.interval_name) AS t_int_name,
  coalesce(l.b_interval, p.b_interval) AS b_interval,
  coalesce(lbi.interval_name, pbi.interval_name) AS b_int_name,
  l.color,
  coalesce(l.lith_ids, '{}') AS lith_id,
  coalesce(l.all_lith_types, '{}') AS lith_types,
  coalesce(l.all_lith_classes, '{}') AS lith_classes,
  coalesce(l.strat_name_ids, '{}') AS strat_name_id,
  coalesce(l.unit_ids, '{}') AS unit_ids
FROM units u
/* `scale` prunes `maps.polygons` to one partition before the key lookup. */
JOIN maps.polygons p ON p.map_id = u.map_id AND p.scale = u.scale
JOIN maps.sources s ON s.source_id = u.source_id
LEFT JOIN map_bounds.map_layer ml ON ml.id = u.map_layer_id
LEFT JOIN maps.sources mls ON mls.source_id = ml.source_id
LEFT JOIN maps.sources v ON v.source_id = u.member_id
LEFT JOIN maps.map_legend ON map_legend.map_id = u.map_id
LEFT JOIN maps.legend l ON l.legend_id = map_legend.legend_id
LEFT JOIN macrostrat.intervals lti ON lti.id = l.t_interval
LEFT JOIN macrostrat.intervals pti ON pti.id = p.t_interval
LEFT JOIN macrostrat.intervals lbi ON lbi.id = l.b_interval
LEFT JOIN macrostrat.intervals pbi ON pbi.id = p.b_interval
ORDER BY u.priority_path DESC NULLS LAST, p.map_id;
