var express = require("express");
var carto = express.Router();
var larkin = require("../larkin");

carto.route("/")
  .get(function(req, res, next) {
    larkin.defineCategory("carto", function(error, routes) {
      res.json({
        "success": routes
      });
    });
  }
);

carto.route("/small")
  .get(function(req, res, next) {
    require("./small")(req, res, next);
  });

module.exports = carto;
