var api = require("./api"),
    larkin = require("./larkin");

// Establish a connection to the database
larkin.connectMySQL();

api.route("/")
  .get(require("./root"));

api.route("/column")
  .get(require("./column"));

api.route("/columns")
  .get(require("./columns"));

api.route("/sections")
  .get(require("./sections"));

api.route("/unit_contacts")
  .get(require("./unit_contacts"));

api.route("/units")
  .get(require("./units"));

api.route("/fossils")
  .get(require("./fossils"));

api.route("/pbdb_report")
  .get(require("./pbdb_report"));

api.route("/stats")
  .get(require("./stats"));

api.route("/defs")
  .get(require("./definitions"));

api.route("/defs/lithologies")
  .get(require("./defs_lithologies"));

api.route("/defs/lithology_attributes")
  .get(require("./defs_lithology_attributes"));

api.route("/defs/environments")
  .get(require("./defs_environments"));

api.route("/defs/intervals")
  .get(require("./defs_intervals"));

api.route("/defs/projects")
  .get(require("./defs_projects"));

api.route("/defs/strat_names")
  .get(require("./defs_strat_names"));

api.route("/defs/timescales")
  .get(require("./defs_timescales"));

api.route("/defs/measurements")
  .get(require("./defs_measurements"));

api.route("/section_stats")
  .get(require("./section_stats"));

api.route("/paleogeography")
  .get(require("./paleogeography"));

api.route("/geologic_units")
  .get(require("./geologic_units"));

api.route("/geologic_units/intersection")
  .get(require("./geologic_units_intersection"));

api.route("/geologic_units/map")
  .get(require("./geologic_units_map"));

api.route("/mobile")
  .get(require("./mobile"));
  
api.route("/mobile/point")
  .get(require("./mobile_point"));

api.route("/mobile/point_details")
  .get(require("./mobile_point_details"));

api.route("/mobile/fossil_collections")
  .get(require("./mobile_fossil_collections"));

api.route("/editing/map")
  .get(require("./editing_map"));

api.route("/editing/map/update")
  .post(require("./editing_map_update"));

api.route("/editing/section")
  .get(require("./editing_section"));

api.route("/editing/units/update")
  .put(require("./editing_units_update"));

api.route("*")
  .get(require("./catchall"));

api.use(function(err, req, res, next) {
  if(err.status !== 404) {
    return next();
  } else if (err.status === 404) {
    larkin.error(req, res, next, "404: Page not found", 404);
  } else {
    larkin.error(req, res, next, "500: Internal Server Error", 500);
  }
});

module.exports = api;
