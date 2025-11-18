/**
  Find all stratigraphic names that can be associated with any
  unit in a column.

  Parameters:
  - col_id: The identity of a column
  - use_adjacent_cols: Allow units from adjacent columns
  - use_concepts: Allow concepts
  - use_column_units: Allow units directly linked to colums
  - use_footprint_index: Directly link stratigraphic names from the footprint index
      (allows names that are not yet associated with column units to be matched)

  All `use_*` parameters are boolean and should be set to true for the most expansive matching
 */

WITH RECURSIVE cols AS (
  SELECT
      col_id,
      ST_SetSRID(ca.col_area, 4326) as col_area
  FROM macrostrat.col_areas ca
  JOIN macrostrat.cols c ON c.id = ca.col_id
  WHERE c.status_code = 'active'
), selected_col AS (
    SELECT * FROM cols WHERE col_id = :col_id
), adjacent_cols AS (
    SELECT cols.*,
           cols.col_id = sel.col_id selected
    FROM cols
    JOIN selected_col sel
      ON ST_Intersects(cols.col_area, ST_Buffer(sel.col_area, 0.01))
    WHERE :use_adjacent_cols
       OR cols.col_id = sel.col_id
), strat_units AS (
  SELECT
    sn.id strat_name_id,
    sn.strat_name,
    sn.rank,
    st.parent::integer parent_id,
    concept_id
  FROM macrostrat.strat_names sn
  LEFT JOIN macrostrat.strat_tree st
    ON sn.id = st.child
), base_unit AS (
  SELECT sn.*,
         u.id unit_id,
         u.col_id,
         0 AS depth
  FROM strat_units sn
  JOIN macrostrat.unit_strat_names usn ON sn.strat_name_id = usn.strat_name_id
  JOIN macrostrat.units u ON usn.unit_id = u.id
  JOIN adjacent_cols cols
    ON cols.col_id = u.col_id
), strat_name_children AS (
  -- Unit at this level
  SELECT * FROM base_unit
  UNION ALL
  -- Children
  SELECT
   sn2.*,
   snt.unit_id,
   snt.col_id,
   snt.depth + 1 AS depth
 FROM strat_units sn2
 JOIN strat_name_children snt
   ON snt.parent_id = sn2.strat_name_id
), strat_name_parents AS (
 SELECT * FROM base_unit
 UNION ALL
 -- Parents
 SELECT
   sn2.*,
   snt.unit_id,
   snt.col_id,
   snt.depth - 1 AS depth
 FROM strat_units sn2
 JOIN strat_name_parents snt
   ON snt.strat_name_id = sn2.parent_id
), all_results AS (
  SELECT * FROM strat_name_children
  UNION ALL
  SELECT * FROM strat_name_parents
), with_linked_concepts AS (
  /** Expand the search to higher-order "concepts" linked to units */
  SELECT
    *,
    0 AS sort_order,
    'column unit' basis
  FROM all_results
  WHERE :use_column_units
  UNION ALL
  SELECT
    sn.strat_name_id,
    snm.name strat_name,
    null,
    null,
    snm.concept_id,
    sn.unit_id,
    sn.col_id,
    sn.depth,
    1 AS sort_order,
    'concept' basis
    FROM all_results sn
  JOIN macrostrat.strat_names_meta snm
    ON sn.concept_id = snm.concept_id
  -- Toggle to turn off concept linking
  WHERE :use_concepts
  UNION ALL
  -- Synonyms
  SELECT
    sn3.id strat_name_id,
    sn3.strat_name,
    sn3.rank,
    null,
    snm.concept_id,
    sn.unit_id,
    sn.col_id,
    sn.depth,
    2 AS sort_order,
    'synonym' basis
  FROM macrostrat.strat_names sn3
  JOIN macrostrat.strat_names_meta snm
    ON sn3.concept_id = snm.concept_id
  JOIN all_results sn
    ON sn.concept_id = snm.concept_id
  WHERE :use_synonyms
    AND NOT EXISTS (
      SELECT 1
      FROM all_results
      WHERE strat_name_id = sn3.id
    )
),
with_footprints_index AS (
  -- Prioritize direct linking over the footprint index
  SELECT
    strat_name_id,
    lc.strat_name,
    rank,
    parent_id,
    concept_id,
    lc.unit_id,
    lc.col_id,
    depth,
    lc.basis,
    lu.t_age,
    lu.b_age,
    sort_order,
    (col_id = (SELECT col_id FROM selected_col))::integer AS is_selected_column
  FROM with_linked_concepts lc
  JOIN macrostrat.lookup_units lu
    ON lc.unit_id = lu.unit_id
  UNION ALL
  SELECT
    strat_name_id,
    snf.rank_name strat_name,
    null rank,
    null parent_id,
    snf.concept_id,
    null unit_id,
    null col_id,
    null depth,
    'footprint index' AS basis,
    best_t_age t_age,
    best_b_age b_age,
    3 AS sort_order,
    ST_Intersects(geom, (SELECT col_area FROM selected_col))::integer
  FROM macrostrat.strat_name_footprints snf
  JOIN adjacent_cols
    ON ST_Intersects(geom, col_area)
  -- Use a permissive spatial filter
  WHERE best_t_age IS NOT NULL
    AND best_b_age IS NOT NULL
    -- Only use the index if the name is not already linked
    AND NOT EXISTS (
      SELECT 1
      FROM with_linked_concepts
      WHERE strat_name_id = snf.strat_name_id
    )
    AND :use_footprint_index
  ORDER BY sort_order, is_selected_column DESC NULLS LAST
)
SELECT DISTINCT ON (sort_order, is_selected_column, strat_name_id)
  sort_order priority,
  strat_name_id,
  strat_name,
  rank strat_rank,
  parent_id,
  concept_id,
  unit_id,
  col_id,
  depth,
  basis,
  CASE
    WHEN is_selected_column != 0
    THEN 'containing column'
    ELSE 'adjacent column'
  END AS spatial_basis,
  t_age min_age,
  b_age max_age
FROM with_footprints_index
ORDER BY sort_order, is_selected_column DESC, strat_name_id;
