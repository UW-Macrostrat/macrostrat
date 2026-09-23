/** Rebuild one source's rows in `lookup_<scale>`.

  Two grains, kept apart. Strat names and lithologies are matched per legend
  entry, so every polygon of an entry carries the same ones: they are decided
  once per entry and joined out -- 6,816 entries rather than 312,286 polygons on
  SGMC. Units, and the ages and colour that follow from them, are per polygon,
  and correctly: units belong to columns, and 6,953 of 20,130 legend entries
  have polygons resolving to different units.

  Run as one transaction (see `lookup.py`), so the source is never seen with its
  rows deleted and not yet rebuilt.
*/
DELETE FROM {lookup_table}
WHERE map_id IN (
  SELECT map_id FROM {scale_table} WHERE source_id = :source_id
);

INSERT INTO {lookup_table} (
  map_id,
  legend_id,
  unit_ids,
  strat_name_ids,
  concept_ids,
  strat_name_children,
  lith_ids,
  lith_types,
  lith_classes,
  best_age_top,
  best_age_bottom,
  color
)
WITH

/* The same ranking as `legend-lookup/strat-name-ids.sql`: each entry keeps its
   strongest matches. See there for the order. */
ranked AS (
  SELECT
    lsn.legend_id,
    lsn.strat_name_id,
    rank() OVER (
      PARTITION BY lsn.legend_id
      ORDER BY
        lsn.is_manual DESC,
        CASE lsn.match_field
          WHEN 'strat_name' THEN 0
          WHEN 'name' THEN 1
          ELSE 2
        END,
        CASE
          WHEN lsn.age_overlaps THEN 0
          WHEN NOT lsn.age_overlaps THEN 1
          ELSE 2
        END,
        lsn.location_basis
    ) AS tier
  FROM maps.legend_strat_names lsn
  JOIN maps.legend l ON l.legend_id = lsn.legend_id
  WHERE l.source_id = :source_id
),

legend_strat_names AS (
  SELECT legend_id, array_agg(DISTINCT strat_name_id) AS strat_name_ids
  FROM ranked
  WHERE tier = 1
  GROUP BY legend_id
),

/* The matched names' own concepts -- not their ancestors', which
   `legend-lookup` adds to `maps.legend.concept_ids` -- and every name that
   points at one of them from any rank column. */
legend_concepts AS (
  SELECT
    sn.legend_id,
    array_agg(DISTINCT lsn.concept_id) AS concept_ids,
    (
      SELECT array_agg(DISTINCT child.strat_name_id)
      FROM macrostrat.lookup_strat_names child
      WHERE child.bed_id = ANY(sn.strat_name_ids)
        OR child.mbr_id = ANY(sn.strat_name_ids)
        OR child.fm_id = ANY(sn.strat_name_ids)
        OR child.gp_id = ANY(sn.strat_name_ids)
        OR child.sgp_id = ANY(sn.strat_name_ids)
    ) AS strat_name_children
  FROM legend_strat_names sn
  JOIN macrostrat.lookup_strat_names lsn
    ON lsn.strat_name_id = ANY(sn.strat_name_ids)
  GROUP BY sn.legend_id, sn.strat_name_ids
),

/* Lithologies from the map's own text only -- the lithologies of matched units
   are not included. Each entry takes the first field that matched anything, in
   the order `lith`, `descrip`, `name`, `comments`. */
lith_bases AS (
  SELECT ll.legend_id, array_agg(DISTINCT ll.basis_col) AS bases
  FROM maps.legend_liths ll
  JOIN maps.legend l ON l.legend_id = ll.legend_id
  WHERE l.source_id = :source_id
  GROUP BY ll.legend_id
),

legend_lith_ids AS (
  SELECT
    ll.legend_id,
    array_agg(DISTINCT liths.lith_equiv) AS lith_ids,
    array_agg(DISTINCT liths.lith_type) AS lith_types,
    array_agg(DISTINCT liths.lith_class) AS lith_classes
  FROM maps.legend_liths ll
  JOIN lith_bases b ON b.legend_id = ll.legend_id
  JOIN macrostrat.liths ON liths.id = ll.lith_id
  WHERE ll.basis_col =
    CASE
      WHEN 'lith' = ANY(b.bases) THEN 'lith'
      WHEN 'descrip' = ANY(b.bases) THEN 'descrip'
      WHEN 'name' = ANY(b.bases) THEN 'name'
      WHEN 'comments' = ANY(b.bases) THEN 'comments'
      ELSE ''
    END
  GROUP BY ll.legend_id
),

/* Every unit match a polygon carries, and the age range they span.

   No tier to choose between: `units.py` excludes a polygon from every later
   pass once it has matched, so a `map_id` holds exactly one `basis_col` -- true
   of all 651,909 of them. The ages are aggregated in the same pass; they were
   six correlated subqueries per polygon. */
unit_matches AS (
  SELECT
    mu.map_id,
    array_agg(DISTINCT mu.unit_id) AS unit_ids,
    min(ui.t_age) AS t_age,
    max(ui.b_age) AS b_age
  FROM {scale_table} q
  JOIN maps.map_units mu ON mu.map_id = q.map_id
  LEFT JOIN macrostrat.lookup_unit_intervals ui ON ui.unit_id = mu.unit_id
  WHERE q.source_id = :source_id
  GROUP BY mu.map_id
),

/* A polygon's age is its units' where it has any, and its own intervals'
   otherwise. */
polygons AS (
  SELECT
    q.map_id,
    ml.legend_id,
    q.name,
    u.unit_ids,
    coalesce(u.t_age, ti.age_top) AS best_age_top,
    coalesce(u.b_age, tb.age_bottom) AS best_age_bottom
  FROM {scale_table} q
  LEFT JOIN maps.map_legend ml ON ml.map_id = q.map_id
  LEFT JOIN unit_matches u ON u.map_id = q.map_id
  LEFT JOIN macrostrat.intervals ti ON ti.id = q.t_interval
  LEFT JOIN macrostrat.intervals tb ON tb.id = q.b_interval
  WHERE q.source_id = :source_id
),

/* The colour of the tightest interval bracketing each age range, excluding the
   New Zealand timescale. Looked up once per distinct range -- 4,435 on SGMC --
   where it was once per polygon, and was 84% of this statement's time. A range
   with a null end matches no interval, and its polygons get no colour. */
colors AS (
  SELECT
    a.best_age_top,
    a.best_age_bottom,
    (
      SELECT i.interval_color
      FROM macrostrat.intervals i
      WHERE i.age_top <= a.best_age_top
        AND i.age_bottom >= a.best_age_bottom
        AND i.id NOT IN (
          SELECT interval_id FROM macrostrat.timescales_intervals
          WHERE timescale_id = 6
        )
      ORDER BY i.age_bottom - i.age_top
      LIMIT 1
    ) AS color
  FROM (SELECT DISTINCT best_age_top, best_age_bottom FROM polygons) a
)

SELECT
  p.map_id,
  p.legend_id,
  coalesce(p.unit_ids, '{{}}'),
  coalesce(sn.strat_name_ids, '{{}}'),
  coalesce(c.concept_ids, '{{}}'),
  coalesce(c.strat_name_children, '{{}}'),
  coalesce(li.lith_ids, '{{}}'),
  coalesce(li.lith_types, '{{}}'),
  coalesce(li.lith_classes, '{{}}'),
  p.best_age_top,
  p.best_age_bottom,
  CASE WHEN p.name ILIKE 'water' THEN '' ELSE col.color END
FROM polygons p
LEFT JOIN legend_strat_names sn ON sn.legend_id = p.legend_id
LEFT JOIN legend_concepts c ON c.legend_id = p.legend_id
LEFT JOIN legend_lith_ids li ON li.legend_id = p.legend_id
LEFT JOIN colors col
  ON col.best_age_top = p.best_age_top
  AND col.best_age_bottom = p.best_age_bottom
