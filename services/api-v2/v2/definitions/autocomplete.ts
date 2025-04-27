/*

select name, type, count(*) from autocomplete where type = 'strat_name_concepts' group by name, type having count(*) > 1 order by count(*) desc;

select name, type, count(*) from autocomplete group by name, type having count(*) > 1 order by count(*) desc;

SELECT concept_id, CONCAT(name, COALESCE(CONCAT(' (', interval_name, ')'), ''))
FROM strat_names_meta
LEFT JOIN intervals ON intervals.id = strat_names_meta.interval_id;

*/
var api = require("../api"),
  larkin = require("../larkin"),
  _ = require("underscore");

module.exports = function (req, res, next) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }

  var categories = [
    "columns",
    "econs",
    "econ_types",
    "econ_classes",
    "environments",
    "environment_types",
    "environment_classes",
    "groups",
    "intervals",
    "lithologies",
    "lithology_types",
    "lithology_classes",
    "lithology_attributes",
    "projects",
    "strat_name_concepts",
    "strat_name_orphans",
    "structures",
    "minerals",
  ];

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
    var limit = "sample" in req.query ? 100 : 100,
      query =
        "sample" in req.query ? "ma%" : req.query.query.toLowerCase() + "%";

    larkin.queryPg(
      "burwell",
      "SELECT id::integer, name, type, category FROM macrostrat.autocomplete WHERE name ILIKE :query AND type = ANY(:types) LIMIT :limit",
      { query: query, types: types, limit: limit },
      function (error, result) {
        console.log(result);
        if (error) {
          larkin.error(req, res, next, error);
        } else {
          var parsed = _.groupBy(result.rows, function (each) {
            return each.type;
          });
          var keys = Object.keys(parsed);
          //TODO format the json output identical to prod

          for (var i = 0; i < keys.length; i++) {
            for (var j = 0; j < parsed[keys[i]].length; j++) {
              delete parsed[keys[i]][j].type;
            }
          }

          larkin.sendData(
            req,
            res,
            next,
            {
              format: "json",
              compact: true,
            },
            {
              data: parsed,
            },
          );
        }
      },
    );
  } else {
    return larkin.info(req, res, next);
  }
};
