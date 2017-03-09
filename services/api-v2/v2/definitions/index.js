var express = require("express");
var definitions = express.Router();
var larkin = require("../larkin");

definitions.route("/")
  .get(function(req, res, next) {
    larkin.defineCategory("definitions", function(error, routes) {
      res.json({
        "success": routes
      });
    });
  }
);

definitions.route("/autocomplete")
  .get(require("./autocomplete"));

definitions.route("/define")
  .get(require("./define"));

definitions.route("/columns")
  .get(function(req, res, next) {
    require("./columns")(req, res, next);
  });

definitions.route("/econs")
  .get(function(req, res, next) {
    require("./econs")(req, res, next);
  });

definitions.route("/environments")
  .get(function(req, res, next) {
    require("./environments")(req, res, next);
  });

definitions.route("/groups")
  .get(function(req, res, next) {
    require("./groups")(req, res, next);
  });

definitions.route("/intervals")
  .get(function(req, res, next) {
    require("./intervals")(req, res, next);
  });

definitions.route("/languages")
  .get(function(req, res, next) {
    require("./languages")(req, res, next);
  });

definitions.route("/lithologies")
  .get(function(req, res, next) {
    require("./lithologies")(req, res, next);
  });

definitions.route("/lithology_attributes")
  .get(function(req, res, next) {
    require("./lithology_attributes")(req, res, next);
  });

definitions.route("/measurements")
  .get(function(req, res, next) {
    require("./measurements")(req, res, next);
  });

definitions.route("/minerals")
  .get(function(req, res, next) {
    require("./minerals")(req, res, next);
  });

definitions.route("/plates")
  .get(function(req, res, next) {
    require("./plates")(req, res, next);
  });

definitions.route("/projects")
  .get(function(req, res, next) {
    require("./projects")(req, res, next);
  });

definitions.route("/sources")
  .get(function(req, res, next) {
    require("./sources")(req, res, next);
  });

definitions.route("/strat_names")
  .get(function(req, res, next) {
    require("./strat_names")(req, res, next);
  });

definitions.route("/strat_name_concepts")
  .get(function(req, res, next) {
    require("./strat_name_concepts")(req, res, next);
  });

definitions.route("/structures")
  .get(function(req, res, next) {
    require("./structures")(req, res, next);
  });

definitions.route("/timescales")
  .get(function(req, res, next) {
    require("./timescales")(req, res, next);
  });

definitions.route("/refs")
  .get(function(req, res, next) {
    require("./refs")(req, res, next);
  });


module.exports =  definitions;
