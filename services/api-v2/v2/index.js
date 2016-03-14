var api = require("./api"),
    larkin = require("./larkin");


// Establish a connection to the database
larkin.connectMySQL();
larkin.setupCache();

api.route("/")
  .get(require("./root"));

api.route("/vtiles/burwell/:z/:x/:y")
  .get(require("./vtiles"));

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

api.route("/defs/define")
  .get(require("./defs/define"));

api.route("/defs/columns")
  .get(function(req, res, next) {
    require("./defs/columns")(req, res, next);
  });

api.route("/defs/econs")
  .get(function(req, res, next) {
    require("./defs/econs")(req, res, next);
  });

api.route("/defs/environments")
  .get(function(req, res, next) {
    require("./defs/environments")(req, res, next);
  });

api.route("/defs/groups")
  .get(function(req, res, next) {
    require("./defs/groups")(req, res, next);
  });

api.route("/defs/intervals")
  .get(function(req, res, next) {
    require("./defs/intervals")(req, res, next);
  });

api.route("/defs/lithologies")
  .get(function(req, res, next) {
    require("./defs/lithologies")(req, res, next);
  });

api.route("/defs/lithology_attributes")
  .get(function(req, res, next) {
    require("./defs/lithology_attributes")(req, res, next);
  });

api.route("/defs/measurements")
  .get(function(req, res, next) {
    require("./defs/measurements")(req, res, next);
  });

api.route("/defs/plates")
  .get(function(req, res, next) {
    require("./defs/plates")(req, res, next);
  });

api.route("/defs/projects")
  .get(function(req, res, next) {
    require("./defs/projects")(req, res, next);
  });

api.route("/defs/sources")
  .get(function(req, res, next) {
    require("./defs/sources")(req, res, next);
  });

api.route("/defs/strat_names")
  .get(function(req, res, next) {
    require("./defs/strat_names")(req, res, next);
  });

api.route("/defs/strat_name_concepts")
  .get(function(req, res, next) {
    require("./defs/strat_name_concepts")(req, res, next);
  });

api.route("/defs/timescales")
  .get(function(req, res, next) {
    require("./defs/timescales")(req, res, next);
  });

api.route("/defs/refs")
  .get(function(req, res, next) {
    require("./defs/refs")(req, res, next);
  });

api.route("/paleogeography")
  .get(require("./paleogeography"));

api.route("/geologic_units/gmna")
  .get(require("./geologic_units_gmna"));

api.route("/geologic_units/gmus")
  .get(require("./geologic_units_gmus"));

api.route("/geologic_units/burwell")
  .get(function(req, res, next) {
    require("./geologic_units_burwell")(req, res, next);
  });

api.route("/geologic_units/burwell/nearby")
  .get(require("./geologic_units_burwell_nearby"));

api.route("/elevation")
  .get(require("./elevation"));

api.route("/mobile")
  .get(require("./mobile/mobile"));

api.route("/mobile/point")
  .get(require("./mobile/point"));

api.route("/mobile/point_details")
  .get(require("./mobile/point_details"));

api.route("/mobile/fossil_collections")
  .get(require("./mobile/fossil_collections"));

api.route("/mobile/macro_summary")
  .get(require("./mobile/macro_summary"));

api.route("/grids")
  .get(require("./grids/grids"));

api.route("/grids/latitude")
  .get(require("./grids/latitude"));

api.route("/grids/longitude")
  .get(require("./grids/longitude"));

api.route("/grids/lithologies")
  .get(require("./grids/lithologies"));

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
