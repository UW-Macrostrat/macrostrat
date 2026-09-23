/** Each legend entry's lithologies: the preferred ones, then all of them.

  `lith_ids` takes the first field that matched anything, in the order `lith`,
  `descrip`, `name`, `comments`; `all_lith_ids` takes every field. Both are from
  the map's own text only -- the lithologies of matched units are not included.
*/
WITH lith_bases AS (
  SELECT ll.legend_id, array_agg(DISTINCT ll.basis_col) AS bases
  FROM maps.legend_liths ll
  JOIN maps.legend l ON l.legend_id = ll.legend_id
  WHERE l.source_id = :source_id
  GROUP BY ll.legend_id
),

liths AS (
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
)

UPDATE maps.legend
SET
  lith_ids = liths.lith_ids,
  lith_types = liths.lith_types,
  lith_classes = liths.lith_classes
FROM liths
WHERE liths.legend_id = legend.legend_id;

UPDATE maps.legend
SET
  all_lith_ids = all_liths.lith_ids,
  all_lith_types = all_liths.lith_types,
  all_lith_classes = all_liths.lith_classes
FROM (
  SELECT
    ll.legend_id,
    array_agg(DISTINCT liths.lith_equiv) AS lith_ids,
    array_agg(DISTINCT liths.lith_type) AS lith_types,
    array_agg(DISTINCT liths.lith_class) AS lith_classes
  FROM maps.legend_liths ll
  JOIN maps.legend l ON l.legend_id = ll.legend_id
  JOIN macrostrat.liths ON liths.id = ll.lith_id
  WHERE l.source_id = :source_id
  GROUP BY ll.legend_id
) all_liths
WHERE all_liths.legend_id = legend.legend_id
