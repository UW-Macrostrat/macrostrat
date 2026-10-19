var express = require("express");
var grids = express.Router();
var larkin = require("../larkin");

grids.route("/").get(function (req, res, next) {
  larkin.defineCategory("grids", function (error, routes) {
    res.json({
      success: routes,
    });
  });
});

grids.route("/latitude").get(require("./latitude"));

grids.route("/longitude").get(require("./longitude"));

grids.route("/lithologies").get(require("./lithologies"));

module.exports = grids;
