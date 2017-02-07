var api = require("./api"),
    larkin = require("./larkin");

// Establish a connection to the database
larkin.connectMySQL();
larkin.setupCache();

// Load route categories
api.use("/carto", require("./carto"));
api.use("/defs", require("./definitions"))
api.use("/grids", require("./grids"));
api.use("/mobile", require("./mobile"));

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

api.route("/geologic_units/burwell/points")
  .get(require("./geologic_units_burwell_points"));

api.route("/elevation")
  .get(function(req, res, next) {
    require("./elevation")(req, res, next);
  });

api.route("/measurements")
  .get(require("./measurements"));

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
