var api = require("./api"),
    larkin = require("./larkin");


// Establish a connection to the database
larkin.connectMySQL();

api.route("/")
  .get(require("./root"));

api.route("/meta")
  .get(require("./meta"));
  
api.route("/changes")
  .get(function(req, res, next) {
    res.sendFile(__dirname + "/changes.html");
  });

api.route("/columns")
  .get(require("./columns"));

api.route("/sections")
  .get(require("./sections"));

api.route("/units")
  .get(function(req, res, next) {
    require("./units")(req, res, next);
  });

api.route("/fossils")
  .get(require("./fossils"));

api.route("/stats")
  .get(require("./stats"));

api.route("/defs")
  .get(require("./defs/definitions"));

api.route("/defs/autocomplete")
  .get(require("./defs/autocomplete"));

api.route("/defs/columns")
  .get(require("./defs/columns"));

api.route("/defs/econs")
  .get(require("./defs/econs"));

api.route("/defs/environments")
  .get(require("./defs/environments"));

api.route("/defs/groups")
  .get(require("./defs/groups"));

api.route("/defs/intervals")
  .get(require("./defs/intervals"));

api.route("/defs/lithologies")
  .get(require("./defs/lithologies"));

api.route("/defs/lithology_attributes")
  .get(require("./defs/lithology_attributes"));

api.route("/defs/measurements")
  .get(require("./defs/measurements"));

api.route("/defs/plates")
  .get(require("./defs/plates"));

api.route("/defs/projects")
  .get(require("./defs/projects"));

api.route("/defs/sources")
  .get(require("./defs/sources"));

api.route("/defs/strat_names")
  .get(function(req, res, next) {
    require("./defs/strat_names")(req, res, next);
  });

api.route("/defs/timescales")
  .get(require("./defs/timescales"));

api.route("/defs/refs")
  .get(require("./defs/refs"));

api.route("/paleogeography")
  .get(require("./paleogeography"));

api.route("/geologic_units/gmna")
  .get(require("./geologic_units_gmna"));

api.route("/geologic_units/gmus")
  .get(require("./geologic_units_gmus"));

api.route("/geologic_units/burwell")
  .get(require("./geologic_units_burwell"));

api.route("/mobile")
  .get(require("./mobile/mobile"));

api.route("/mobile/point")
  .get(require("./mobile/point"));

api.route("/mobile/point_details")
  .get(require("./mobile/point_details"));

api.route("/mobile/fossil_collections")
  .get(require("./mobile/fossil_collections"));

api.route("/editing")
  .get(require("./editing/editing"));

api.route("/editing/map")
  .get(require("./editing/map"));

api.route("/editing/map/update")
  .post(require("./editing/map_update"));

api.route("/editing/section")
  .get(require("./editing/section"));

api.route("/editing/units/update")
  .put(require("./editing/units_update"));

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
