SET SEARCH_PATH to macrostrat, public;

DROP TABLE IF EXISTS macrostrat.lookup_unit_attrs_api_new;
DROP TABLE IF EXISTS macrostrat.lookup_unit_attrs_api_old;
CREATE TABLE macrostrat.lookup_unit_attrs_api_new (LIKE lookup_unit_attrs_api);

/** Note: these comp_prop calculations are as follows:
  - For dominant liths, the comp_prop is 5 / (5 * number of dominant liths + number of subordinate liths)
  - For subordinate liths, the comp_prop is 1 / (5 * number of dominant liths + number of subordinate liths)
  - If there are no dominant liths, then the comp_prop for all liths is 1 / number of subordinate liths

  Basically, dominant props are weighted higher than subordinate liths by a factor of 5

  Note: these calculations don't appear to work correctly right now...
*/

WITH d AS (
  SELECT a.unit_id,
    (5 / (COALESCE(bdom, 0) + (adom * 5))) AS dom_p
  FROM (
    SELECT unit_id,
      COUNT(id) adom,
      'dom' AS dom
    FROM unit_liths
    WHERE dom = 'dom'
    GROUP BY unit_id
  ) a
  LEFT JOIN (
    SELECT unit_id,
      COUNT(id) bdom,
      'sub' AS dom
    FROM unit_liths
    WHERE dom = 'sub'
    GROUP BY unit_id
  ) b ON b.unit_id = a.unit_id
)
UPDATE unit_liths ul
SET comp_prop = d.dom_p
FROM d
WHERE d.unit_id = ul.unit_id
  AND 'dom' = ul.dom;

WITH s AS (
  SELECT
    a.unit_id,
    (1 / (COALESCE(bdom, 0) + (adom * 5))) AS sub_p
  FROM (
    SELECT
      unit_id,
      count(id) adom,
      'dom' AS dom
    FROM unit_liths
    WHERE dom = 'dom'
    GROUP BY unit_id
  ) a
  LEFT JOIN (
    SELECT
      unit_id,
      count(id) bdom,
      'sub' AS dom
    FROM unit_liths
    WHERE dom = 'sub'
    GROUP BY unit_id
  ) b ON b.unit_id = a.unit_id
)
UPDATE unit_liths ul
SET comp_prop = s.sub_p
FROM s
WHERE s.unit_id = ul.unit_id
 AND 'sub' = ul.dom;

WITH a AS (
  SELECT unit_id,
    json_build_object(
      'lith_id', lith_id,
      'name', lith,
      'type', lith_type,
      'class', lith_class,
      'prop', comp_prop,
      'atts', TO_JSON(ARRAY_REMOVE(ARRAY_AGG(lith_atts.lith_att), NULL))
    ) AS lith
  FROM unit_liths
  LEFT JOIN liths ON lith_id = liths.id
  LEFT JOIN unit_liths_atts ON unit_liths.id = unit_liths_atts.unit_lith_id
  LEFT JOIN lith_atts ON unit_liths_atts.lith_att_id = lith_atts.id
  GROUP BY unit_liths.id, liths.id, liths.lith, lith_type, lith_class, comp_prop
)
INSERT INTO macrostrat.lookup_unit_attrs_api_new (
  unit_id,
  lith
)
-- We keep this in text format for now for parallelism with v1, but we should consider
-- changing this to JSONB in the future
SELECT unit_id, json_agg(lith)::text::bytea FROM a
GROUP BY unit_id;
