SET SEARCH_PATH to macrostrat, public;

DROP TABLE IF EXISTS macrostrat.lookup_unit_attrs_api_new;
DROP TABLE IF EXISTS macrostrat.lookup_unit_attrs_api_old;
CREATE TABLE macrostrat.lookup_unit_attrs_api_new (LIKE lookup_unit_attrs_api);

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

