/**
  Extended attributes for strat names tree
 */
SELECT
  parent, -- this_name has been renamed to parent
  child,
  sn1.strat_name parent_strat_name,
  sn1.rank parent_rank,
  sn2.strat_name child_strat_name,
  sn2.rank child_rank
FROM macrostrat.strat_tree
JOIN macrostrat.strat_names sn1
ON parent = sn1.id
JOIN macrostrat.strat_names sn2
ON child = sn2.id
WHERE child = :child
  AND rel = 'parent' and sn1.rank != '';

/* Count of number of children per parent */
SELECT
  parent parent_id,
  array_agg(child) children,
  count(child) n_children
FROM macrostrat.strat_tree
GROUP BY parent;

/* Unified count of parents per child */
SELECT
  id strat_name_id,
  strat_name,
  parents,
  children,
  n_parents,
  n_children
FROM macrostrat.strat_names
LEFT JOIN (SELECT parent           id,
                  ARRAY_AGG(child) children,
                  COUNT(child)     n_children
           FROM macrostrat.strat_tree
           GROUP BY parent) cc
USING (id)
LEFT JOIN (
  SELECT child id,
  ARRAY_AGG(parent) parents,
  COUNT(parent)    n_parents
  FROM macrostrat.strat_tree
  GROUP BY child
) pc
USING (id)

/** Seven strat names have more than one parent
60687, 64337, 66418, 4092, 5012, 1712, 80846
*/


SELECT
  concept_id,
  COUNT(*) n_names,
  array_agg(strat_name) strat_names
FROM macrostrat.strat_names
GROUP BY concept_id;

SELECT ref_id FROM macrostrat.strat_names WHERE concept_id IS Null;

/** List of concept IDs by data domain */
WITH a as (
  SELECT concept_id,
         (REGEXP_MATCH(url, '^(https?\:\/\/)([A-Za-z0-9\.]+)'))[2] domain
  FROM macrostrat.strat_names_meta
)
SELECT domain, COUNT(*) n_names FROM a GROUP BY domain;
