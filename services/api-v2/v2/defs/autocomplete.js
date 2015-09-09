/*

DROP TABLE IF EXISTS autocomplete;

CREATE TABLE autocomplete AS
  SELECT * FROM (
    select id, econ as name, 'econs' as type from econs
    union
    select 0 AS id, econ_type AS name, 'econ_types' AS type FROM econs GROUP BY econ_type
    union
    SELECT 0 AS id, econ_class AS name, 'econ_classes' AS type FROM econs GROUP BY econ_class
    union
    select id, environ as name, 'environments' as type from environs
    union
    select 0 AS id, environ_type AS name, 'environment_types' AS type FROM environs GROUP BY environ_type
    union
    select 0 AS id, environ_class AS name, 'environment_classes' AS type FROM environs GROUP BY environ_class
    union
    select id, concat(lith_att, ' (', att_type, ')') as name, 'lithology_attributes' as type from lith_atts
    union
    select id, project as name, 'projects' as type from projects
    union
    SELECT DISTINCT strat_names_meta.concept_id AS id, name, 'strat_name_concepts' AS type
    FROM strat_names_meta
    JOIN strat_names ON strat_names_meta.concept_id = strat_names.concept_id
    union
    (select id, CONCAT(strat_name, ' ', rank) AS name, 'strat_name_orphans' as type from strat_names WHERE concept_id = 0)
    union
    select id, col_name as name, 'columns' as type from cols
    union
    select id, col_group_long as name, 'groups' as type from col_groups
    union
    SELECT id, lith AS name, 'lithologies' AS type
    FROM liths
    WHERE lith != lith_type AND lith != lith_class
    union
    SELECT 0 AS id, lith AS name, 'lithology_types' AS type
    FROM liths
    WHERE lith = lith_type
    union
    SELECT 0 AS id, lith AS name, 'lithology_classes' AS type
    FROM liths
    WHERE lith = lith_class
    union
    select id, interval_name as name, 'intervals' as type from intervals
  ) i;

  UPDATE autocomplete AS a
    INNER JOIN (
      SELECT concept_id, CONCAT(name, COALESCE(CONCAT(' (', interval_name, ')'), '')) AS name
      FROM strat_names_meta
      LEFT JOIN intervals ON intervals.id = strat_names_meta.interval_id
    ) sub ON a.id = sub.concept_id
  SET a.name = sub.name
  WHERE a.id IN (
    SELECT id FROM (
      SELECT id
      FROM autocomplete
      WHERE name IN (
        SELECT name
        FROM (
          SELECT name, type, count(*)
          FROM autocomplete
          WHERE type = 'strat_name_concepts'
          GROUP BY name, type
          HAVING count(*) > 1
          ORDER BY count(*) desc
        ) a
      )
    ) b
  ) AND type = 'strat_name_concepts';


  UPDATE autocomplete AS a
    INNER JOIN (
      SELECT concept_id,
        CASE
          WHEN CHAR_LENGTH(province) < 1 THEN name
          ELSE CONCAT(name, ' (', province, ')')
        END AS name
      FROM strat_names_meta
    ) sub ON a.id = sub.concept_id
  SET a.name = sub.name
  WHERE a.id IN (
    SELECT id FROM (
      SELECT id
      FROM autocomplete
      WHERE name IN (
        SELECT name
        FROM (
          SELECT name, type, count(*)
          FROM autocomplete
          WHERE type = 'strat_name_concepts'
          GROUP BY name, type
          HAVING count(*) > 1
          ORDER BY count(*) desc
        ) a
      )
    ) b
  ) AND type = 'strat_name_concepts';

  UPDATE autocomplete AS a
    INNER JOIN (
      SELECT DISTINCT strat_names.id, CONCAT(strat_name, ' (', FO_period, ')') AS name
      FROM strat_names
      JOIN unit_strat_names ON strat_names.id = unit_strat_names.strat_name_id
      JOIN lookup_unit_intervals ON lookup_unit_intervals.unit_id = unit_strat_names.unit_id
    ) sub ON a.id = sub.id
  SET a.name = sub.name
  WHERE a.id IN (
    SELECT id FROM (
      SELECT id
      FROM autocomplete
      WHERE name IN (
        SELECT name
        FROM (
          SELECT name, type, count(*)
          FROM autocomplete
          WHERE type = 'strat_name_orphans'
          GROUP BY name, type
          HAVING count(*) > 1
          ORDER BY count(*) desc
        ) a
      )
    ) b
  ) AND type = 'strat_name_orphans';


ALTER TABLE autocomplete ADD INDEX auto_id (id);
ALTER TABLE autocomplete ADD INDEX auto_name (name);
ALTER TABLE autocomplete ADD INDEX auto_type (type);

select name, type, count(*) from autocomplete where type = 'strat_name_concepts' group by name, type having count(*) > 1 order by count(*) desc;

select name, type, count(*) from autocomplete group by name, type having count(*) > 1 order by count(*) desc;

SELECT concept_id, CONCAT(name, COALESCE(CONCAT(' (', interval_name, ')'), ''))
FROM strat_names_meta
LEFT JOIN intervals ON intervals.id = strat_names_meta.interval_id;




*/
var api = require("../api"),
    larkin = require("../larkin");
    _ = require("underscore");

module.exports = function(req, res, next) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }

  var categories = ["columns", "econs", "econ_types", "econ_classes", "environments", "environment_types", "environmnet_classes", "groups", "intervals", "lithologies", "lithology_types", "lithology_classes", "lithology_attributes", "projects", "strat_name_concepts", "strat_name_orphans"];


  var types = [];

  if (req.query.include) {
    var includes = req.query.include.split(",");
    for (var i = 0; i < includes.length; i++) {
      if (categories.indexOf(includes[i]) > -1) {
        types.push(includes[i]);
      }
    }

  } else if (req.query.exclude) {
    var excludes = req.query.exclude.split(",");
    for (var j = 0; j < categories.length; j++) {
      if (excludes.indexOf(categories[j]) < 0) {
        types.push(categories[j]);
      }
    }
  } else {
    types = categories;
  }

  if (req.query.query || "sample" in req.query) {
    var limit = ("sample" in req.query) ? 100 : 100,
        query = ("sample" in req.query) ? "ma%" : (req.query.query.toLowerCase() + "%");


    larkin.query("SELECT * FROM autocomplete WHERE name LIKE :query AND type IN (:types) LIMIT :limit", {"query": query, "types": types, "limit": limit}, function(error, result) {
      if (error) {
        larkin.error(req, res, next, error);
      } else {
        var parsed = _.groupBy(result, function(each) { return each.type });
        var keys = Object.keys(parsed);

        for (var i = 0; i < keys.length; i++) {
          for (var j = 0; j < parsed[keys[i]].length; j++) {
            delete parsed[keys[i]][j].type;
          }
        }

        larkin.sendCompact(parsed, res, "json");
      }

    });
  } else {
    return larkin.info(req, res, next);
  }

}
