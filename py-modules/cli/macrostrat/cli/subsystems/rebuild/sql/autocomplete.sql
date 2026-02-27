set SEARCH_PATH to macrostrat, public;

-- Two views that we could look into recreating later
DROP VIEW IF EXISTS macrostrat.grouped_autocomplete CASCADE;
DROP VIEW IF EXISTS macrostrat_api.autocomplete CASCADE;

DROP TABLE IF EXISTS macrostrat.autocomplete_new;
DROP TABLE IF EXISTS macrostrat.autocomplete_old;

/* Create table separately to enforce column types */
CREATE TABLE macrostrat.autocomplete_new (
  id       integer   default 0        not null,
  name     varchar(255) default NULL::character varying,
  type     varchar(20)  default ''::character varying not null, -- should change this
  category varchar(10)  default ''::character varying not null -- should change this
);

-- create index autocomplete_new_category_idx1
--   on macrostrat.autocomplete (category);
--
-- create index autocomplete_new_id_idx1
--   on macrostrat.autocomplete (id);
--
-- create index autocomplete_new_name_idx1
--   on macrostrat.autocomplete (name);
--
-- create index autocomplete_new_type_idx1
--   on macrostrat.autocomplete (type);


INSERT INTO macrostrat.autocomplete_new
SELECT * FROM (
  SELECT id, econ AS name, 'econs' AS type, 'econ' AS category
  FROM econs
  UNION
  SELECT 0 AS id, econ_type::text AS name, 'econ_types' AS type, 'econ' AS category
  FROM econs
  WHERE econ != econ_type::text
  GROUP BY econ_type
  UNION
  SELECT 0 AS id, econ_class::text AS name, 'econ_classes' AS type, 'econ' AS category
  FROM econs
  GROUP BY econ_class
  UNION
  SELECT id, environ AS name, 'environments' AS type, 'environ' AS category
  FROM environs
  WHERE environ != environ_class::text
  UNION
  SELECT 0 AS id, environ_type::text AS name, 'environment_types' AS type, 'environ' AS category
  FROM environs
  GROUP BY environ_type
  UNION
  SELECT 0 AS id, environ_class::text AS name, 'environment_classes' AS type, 'environ' AS category
  FROM environs
  GROUP BY environ_class
  UNION
  SELECT id,
        CONCAT(lith_att, ' (', att_type, ')') AS name,
        'lithology_attributes'                AS type,
        'lith_att'                            AS category
  FROM lith_atts
  UNION
  SELECT id, project::text AS name, 'projects' AS type, 'project' AS category
  FROM projects
  UNION
  SELECT DISTINCT strat_names_meta.concept_id AS id,
                 name,
                 'strat_name_concepts'       AS type,
                 'strat_name'                AS category
  FROM strat_names_meta
        JOIN strat_names ON strat_names_meta.concept_id = strat_names.concept_id
  UNION
  (SELECT id,
         CONCAT(strat_name, ' ', rank) AS name,
         'strat_name_orphans'          AS type,
         'strat_name'                  AS category
  FROM strat_names
  WHERE concept_id is null)
  UNION
  SELECT id, col_name AS name, 'columns' AS type, 'column' AS category
  FROM cols
  UNION
  SELECT id, col_group_long AS name, 'groups' AS type, 'group' AS category
  FROM col_groups
  UNION
  SELECT id, lith AS name, 'lithologies' AS type, 'lithology' AS category
  FROM liths
  WHERE lith != lith_type::text
   AND lith != lith_class::text
  UNION
  SELECT 0 AS id, lith_type::text AS name, 'lithology_types' AS type, 'lithology' AS category
  FROM liths
  WHERE lith_type::text != lith_class::text
  GROUP BY lith_type
  UNION
  SELECT 0 AS id, lith_class::text AS name, 'lithology_classes' AS type, 'lithology' AS category
  FROM liths
  GROUP BY lith_class
  UNION
  SELECT id, interval_name AS name, 'intervals' AS type, 'interval' AS category
  FROM intervals
  UNION
  SELECT id, mineral AS name, 'minerals' AS type, 'mineral' AS category
  FROM minerals
  UNION
  SELECT id, structure AS name, 'structures' AS type, 'structure' AS category
  FROM structures
) i;



UPDATE macrostrat.autocomplete_new a
SET name = sub.name
FROM (
  SELECT concept_id, CONCAT(name, COALESCE(CONCAT(' (', interval_name, ')'), '')) AS name
  FROM strat_names_meta
         LEFT JOIN intervals ON intervals.id = strat_names_meta.interval_id
) sub
WHERE a.id IN (
  SELECT id FROM (
    SELECT id
    FROM autocomplete_new
    WHERE name IN (
      SELECT name
      FROM (
        SELECT name, type, count(*)
        FROM autocomplete_new
        WHERE type = 'strat_name_concepts'
        GROUP BY name, type
        HAVING count(*) > 1
        ORDER BY count(*) desc
      ) a
    )
  ) b
) AND type = 'strat_name_concepts'
AND a.id = sub.concept_id;

UPDATE autocomplete_new AS a
SET name = sub.name
FROM (
  SELECT DISTINCT strat_names.id, CONCAT(strat_name, ' (', FO_period, ')') AS name
  FROM strat_names
  JOIN unit_strat_names ON strat_names.id = unit_strat_names.strat_name_id
  JOIN lookup_unit_intervals ON lookup_unit_intervals.unit_id = unit_strat_names.unit_id
) sub
WHERE a.id = sub.id
  AND a.id IN (
    SELECT id FROM (
      SELECT id
      FROM autocomplete_new
      WHERE name IN (
        SELECT name
        FROM (
          SELECT name, type, count(*)
          FROM autocomplete_new
          WHERE type = 'strat_name_orphans'
          GROUP BY name, type
          HAVING count(*) > 1
          ORDER BY count(*) desc
        ) a
      )
    ) b
  ) AND type = 'strat_name_orphans';

ALTER TABLE macrostrat.autocomplete
  RENAME TO autocomplete_old;

ALTER TABLE macrostrat.autocomplete_new
  RENAME TO autocomplete;

