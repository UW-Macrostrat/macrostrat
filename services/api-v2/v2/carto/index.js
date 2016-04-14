var express = require("express");
var carto = express.Router();

carto.use(function(req, res, next) {
  res.header("Access-Control-Allow-Origin", "*");
  res.header("Access-Control-Allow-Headers", "Origin, X-Requested-With, Content-Type, Accept");
  res.header("Access-Control-Allow-Methods", "GET, POST, PUT, OPTIONS");
  next();
});

carto.route("/small")
  .get(function(req, res, next) {
    require("./small")(req, res, next);
  });

module.exports = carto;
