/** Each legend entry's concepts and the names below its matches.

  `concept_ids` is the matched names' own concepts, their ancestors' concepts,
  and -- where the entry matched units -- the concepts of those units' names.
  Reads `strat_name_ids` and `unit_ids`, so it runs after both are set.

  The ancestors come from the flattened rank tree, which the lexicon rebuild
  maintains. This was a five-way self-join over the whole of
  `lookup_strat_names`, with no source predicate, on every run of every source.
*/
WITH matched AS (
  SELECT
    legend.legend_id,
    legend.strat_name_ids,
    coalesce(
      array_agg(DISTINCT anc.id) FILTER (WHERE anc.id IS NOT NULL), '{{}}'
    ) AS ancestor_concept_ids,
    array_agg(DISTINCT lsn.concept_id) AS concept_ids
  FROM maps.legend
  JOIN macrostrat.lookup_strat_names lsn
    ON lsn.strat_name_id = ANY(legend.strat_name_ids)
  JOIN macrostrat.lookup_strat_name_tree tree
    ON tree.strat_name_id = lsn.strat_name_id
  LEFT JOIN LATERAL unnest(tree.ancestor_concept_ids) AS anc(id) ON true
  WHERE legend.source_id = :source_id
  GROUP BY legend.legend_id, legend.strat_name_ids
),

more_strat_names AS (
  SELECT
    legend_id,
    array(
      SELECT DISTINCT unnest(array_cat(concept_ids, ancestor_concept_ids))
    ) AS concept_ids,
    (
      SELECT array_agg(DISTINCT child.strat_name_id)
      FROM macrostrat.lookup_strat_names child
      WHERE child.bed_id = ANY(strat_name_ids)
        OR child.mbr_id = ANY(strat_name_ids)
        OR child.fm_id = ANY(strat_name_ids)
        OR child.gp_id = ANY(strat_name_ids)
        OR child.sgp_id = ANY(strat_name_ids)
    ) AS strat_name_children
  FROM matched
)

UPDATE maps.legend
SET
  concept_ids = CASE
    WHEN array_length(legend.unit_ids, 1) = 0 OR legend.unit_ids IS NULL
      THEN coalesce(more_strat_names.concept_ids, '{{}}')
    ELSE (
      SELECT array(
        SELECT DISTINCT unnest(array_cat(
          coalesce(more_strat_names.concept_ids, '{{}}'),
          array_agg(DISTINCT lsn.concept_id)
        ))
      )
      FROM macrostrat.unit_strat_names usn
      JOIN macrostrat.lookup_strat_names lsn
        ON lsn.strat_name_id = usn.strat_name_id
      WHERE usn.unit_id = ANY(legend.unit_ids)
    )
  END,
  strat_name_children = coalesce(more_strat_names.strat_name_children, '{{}}')
FROM more_strat_names
WHERE more_strat_names.legend_id = legend.legend_id
