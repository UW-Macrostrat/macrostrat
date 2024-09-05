var express = require("express");
var burwellTileServer = require("./burwellTileServer");

var api = express.Router();

api.use(function (req, res, next) {
  res.header("Access-Control-Allow-Origin", "*");
  res.header(
    "Access-Control-Allow-Headers",
    "Origin, X-Requested-With, Content-Type, Accept",
  );
  res.header("Access-Control-Allow-Methods", "GET, POST, PUT, OPTIONS");
  next();
});



// Load the new tile server that has multiple layers (USE ONLY THIS IN V3)
api.use(burwellTileServer);

api.acceptedFormats = {
  standard: {
    json: true,
    csv: true,
  },
  geo: {
    geojson: true,
    topojson: true,
    geojson_bare: true,
    topojson_bare: true,
  },
  bare: {
    geojson_bare: true,
    topojson_bare: true,
  },
};

api.version = 2;
api.license = "CC-BY 4.0";

// Export the module
module.exports = api;
