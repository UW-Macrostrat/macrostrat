/** Keep each legend entry's strongest strat-name matches and drop the rest.

  `rank()` returns every match that ties at the top, which is what the
  `basis_col` ladder did by picking one tier and taking all of it -- but read off
  the evidence columns rather than reassembled from a string.

  Strongest evidence first. A human assertion outranks everything; then the
  field the name was found in -- `strat_name` and `name` are the unit, a
  description is a mention; then temporal corroboration, then spatial.
  Description and comments share a rank, as the ladder this replaces also had
  them.

  This is the same order the forty `WHEN` branches expressed, including the part
  that reads oddly: a buffered footprint demotes *less* than fuzzed time, so
  `_fspace` sorted above `_ftime`. `build-lookup-table.sql` ranks the same way.
*/
WITH ranked AS (
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

strat_names AS (
  SELECT legend_id, array_agg(DISTINCT strat_name_id) AS strat_name_ids
  FROM ranked
  WHERE tier = 1
  GROUP BY legend_id
)

UPDATE maps.legend
SET strat_name_ids = strat_names.strat_name_ids
FROM strat_names
WHERE strat_names.legend_id = legend.legend_id
