/* Flatten the rank tree once, for callers that would otherwise walk it per row.
   Runs after the swap above, against the finished `lookup_strat_names`. */

TRUNCATE macrostrat.lookup_strat_name_tree;

INSERT INTO macrostrat.lookup_strat_name_tree
  (strat_name_id, ancestor_concept_ids, descendant_ids)
WITH ancestry AS (
  /* A name's own concept plus its ancestors' at every rank. `0` is the lexicon's
     "no parent" marker, not a concept. */
  SELECT
    lsn.strat_name_id,
    coalesce(array_agg(DISTINCT anc.concept_id)
             FILTER (WHERE anc.concept_id IS NOT NULL AND anc.concept_id != 0),
             '{}') AS ancestor_concept_ids
  FROM macrostrat.lookup_strat_names lsn
  LEFT JOIN macrostrat.lookup_strat_names anc
    ON anc.strat_name_id IN (
      nullif(lsn.bed_id, 0), nullif(lsn.mbr_id, 0), nullif(lsn.fm_id, 0),
      nullif(lsn.gp_id, 0), nullif(lsn.sgp_id, 0)
    )
  GROUP BY lsn.strat_name_id
),
descent AS (
  /* The mirror: names of lower rank that point at this one through the column
     for its rank. The rank restrictions are load-bearing and are kept exactly as
     the callers had them -- a child is only a descendant through the column that
     matches the parent's own rank.

     `FILTER (WHERE ... IS NOT NULL)` is not decoration: `array_agg(DISTINCT x)`
     over a LEFT JOIN that matched nothing returns `{NULL}`, not NULL, so the
     `coalesce` below would never fire and every row would carry a phantom
     element. */
  SELECT
    parent.strat_name_id,
    coalesce(array_agg(DISTINCT child.strat_name_id)
             FILTER (WHERE child.strat_name_id IS NOT NULL),
             '{}') AS descendant_ids
  FROM macrostrat.lookup_strat_names parent
  LEFT JOIN macrostrat.lookup_strat_names child
    ON (parent.rank = 'Mbr' AND child.rank = 'Bed'
        AND child.mbr_id = parent.strat_name_id)
    OR (parent.rank = 'Fm' AND child.rank IN ('Bed', 'Mbr')
        AND child.fm_id = parent.strat_name_id)
    OR (parent.rank = 'Gp' AND child.rank IN ('Bed', 'Mbr', 'Fm')
        AND child.gp_id = parent.strat_name_id)
    OR (parent.rank = 'SGp' AND child.rank IN ('Bed', 'Mbr', 'Fm', 'Gp')
        AND child.sgp_id = parent.strat_name_id)
  GROUP BY parent.strat_name_id
)
SELECT a.strat_name_id, a.ancestor_concept_ids, d.descendant_ids
FROM ancestry a JOIN descent d USING (strat_name_id);
