/* The legend of any source at a zoom: every legend entry it draws, or only the
   ones drawn within `:bounds`.

   Which maps are drawn is the tiles' answer, read the same way: the source
   answering at the zoom (`serving_source`, the multiscale hop), through its
   faces (`face_layer_for`) where it has them, or as its own single owner where
   it has none -- a map, a materialized compilation, a mosaic member. Each owner's
   content is resolved once (`content_of`).

   `::owners` is filled by the route, with the owners in view and the part of the
   view each one owns (the `visible` form), or with every owner and no geometry
   (the `all` form, which takes each owner's whole legend). Only legend entries
   come back, so a viewport's cost is one indexed polygon lookup per owner rather
   than a row per polygon: a row per polygon over a z6 view of `carto` took
   20 s, this about 1 s. */
WITH target AS (
  SELECT
    map_bounds.serving_source(s.id, CAST(:zoom AS integer)) AS source_id,
    map_bounds.face_layer_for(s.id, CAST(:zoom AS integer)) AS layer_id
  FROM (SELECT map_bounds.resolve_source(CAST(:ident AS text)) AS id) s
),
view AS (
  SELECT ST_SetSRID(ST_GeomFromText(CAST(:bounds AS text)), 4326) AS g
),
owners AS MATERIALIZED (
  ::owners
),
content AS MATERIALIZED (
  SELECT o.geometry, c.source_id, c.footprint, cs.scale
  FROM owners o
  CROSS JOIN LATERAL map_bounds.content_of(o.map_id) c
  JOIN maps.sources cs
    ON cs.source_id = c.source_id
   AND cs.scale = ANY (enum_range(NULL::maps.map_scale)::text[])
),
/* In view, or inside a mosaic member's footprint (its holder's polygons, read
   through it), which entries are drawn is a polygon lookup. Otherwise it is the
   whole legend of the content, which needs no polygons at all. Three branches
   rather than one with ORs: an `IS NULL OR ST_Intersects` condition keeps the
   planner off the polygon index (4.6 s against 1 s on a z6 view of `carto`). */
entries AS (
  SELECT ml.legend_id
  FROM content c
  JOIN maps.polygons p
    ON p.source_id = c.source_id
   AND p.scale = CAST(c.scale AS maps.map_scale)
   AND ST_Intersects(p.geom, c.geometry)
  JOIN maps.map_legend ml ON ml.map_id = p.map_id
  WHERE c.geometry IS NOT NULL
    AND (c.footprint IS NULL OR ST_Intersects(c.footprint, p.geom))
  UNION
  SELECT ml.legend_id
  FROM content c
  JOIN maps.polygons p
    ON p.source_id = c.source_id
   AND p.scale = CAST(c.scale AS maps.map_scale)
   AND ST_Intersects(p.geom, c.footprint)
  JOIN maps.map_legend ml ON ml.map_id = p.map_id
  WHERE c.geometry IS NULL AND c.footprint IS NOT NULL
  UNION
  SELECT l.legend_id
  FROM content c
  JOIN maps.legend l ON l.source_id = c.source_id
  WHERE c.geometry IS NULL AND c.footprint IS NULL
)
SELECT
  m.legend_id,
  m.source_id,
  s.scale,
  REGEXP_REPLACE(m.name, E'[\\n\\r\\f\\u000B\\u0085\\u2028\\u2029]+', ' ', 'g') AS map_unit_name,
  REGEXP_REPLACE(m.strat_name, E'[\\n\\r\\f\\u000B\\u0085\\u2028\\u2029]+', ' ', 'g') AS strat_name,
  m.age,
  REGEXP_REPLACE(m.lith, E'[\\n\\r\\f\\u000B\\u0085\\u2028\\u2029]+', ' ', 'g') AS lith,
  REGEXP_REPLACE(m.descrip, E'[\\n\\r\\f\\u000B\\u0085\\u2028\\u2029]+', ' ', 'g') AS descrip,
  REGEXP_REPLACE(m.comments, E'[\\n\\r\\f\\u000B\\u0085\\u2028\\u2029]+', ' ', 'g') AS comments,
  m.best_age_top::float AS t_age,
  m.best_age_bottom::float AS b_age,
  m.b_interval,
  m.t_interval,
  m.strat_name_ids AS strat_name_id,
  m.unit_ids AS unit_id,
  m.lith_classes,
  m.lith_types,
  m.lith_ids AS lith_id,
  m.color,
  m.area::float,
  m.tiny_area::float,
  m.small_area::float,
  m.medium_area::float,
  m.large_area::float
FROM entries e
JOIN maps.legend m ON m.legend_id = e.legend_id
JOIN maps.sources s ON s.source_id = m.source_id
ORDER BY m.best_age_top NULLS LAST, m.legend_id
LIMIT :limit
