/*

DROP TABLE IF EXISTS autocomplete;

CREATE TABLE autocomplete AS
  SELECT * FROM (
    select id, econ as name, 'econs' as type from econs
    union
    select id, environ as name, 'environments' as type from environs
    union
    select id, concat(lith_att, ' (', att_type, ')') as name, 'lithology_attributes' as type from lith_atts
    union
    select id, project as name, 'projects' as type from projects
    union
    select id, strat_name as name, 'strat_names' as type from strat_names
    union
    select id, col_name as name, 'columns' as type from cols
    union
    select id, col_group as name, 'groups' as type from col_groups
    union
    select id, lith as name, 'lithologies' as type from liths
    union
    select id, interval_name as name, 'intervals' as type from intervals
  ) i;

ALTER TABLE autocomplete ADD INDEX auto_id (id);
ALTER TABLE autocomplete ADD INDEX auto_name (name);
ALTER TABLE autocomplete ADD INDEX auto_type (type);


*/
var api = require("../api"),
    larkin = require("../larkin");
    _ = require("underscore");

module.exports = function(req, res, next) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }

  var categories = ["columns", "econs", "environments", "groups", "intervals", "lithologies", "lithology_attributes", "projects", "strat_names"];


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
