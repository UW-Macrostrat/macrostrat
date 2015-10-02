var express = require("express");
var tilestrata = require('tilestrata');
var sharp = require('tilestrata-sharp');
var mapnik = require('tilestrata-mapnik');
var dependency = require('tilestrata-dependency');
var credentials = require("./credentials");
var customCache = require('./customCache');

var api = express.Router();
var strata = tilestrata.createServer();

api.use(function(req, res, next) {
  res.header("Access-Control-Allow-Origin", "*");
  res.header("Access-Control-Allow-Headers", "Origin, X-Requested-With, Content-Type, Accept");
  res.header("Access-Control-Allow-Methods", "GET, POST, PUT, OPTIONS");
  next();
});

strata.layer("burwell")
    .route("tile@2x.png")
        .use(customCache({
          dir: credentials.tiles.path,
          defaultTile: __dirname + '/default@2x.png'
        }))
        .use(mapnik({
            xml: credentials.tiles.config,
            tileSize: 512,
            scale: 2
        }))
    .route("tile.png")
        .use(customCache({
          dir: credentials.tiles.path,
          defaultTile: __dirname + '/default.png'
        }))
        .use(dependency("burwell", "tile@2x.png"))
        .use(sharp(function(image, sharp) {
            return image.resize(256);
        }));

api.use(tilestrata.middleware({
  server: strata,
  prefix: "/maps"
}))

api.acceptedFormats = {
  "standard": {
    "json": true,
    "csv": true
  },
  "geo": {
    "geojson": true,
    "topojson": true,
    "geojson_bare": true,
    "topojson_bare": true
  },
  "bare": {
    "geojson_bare": true,
    "topojson_bare": true
  }
};

api.version = 2;
api.license = "CC-BY 4.0";

// Export the module
module.exports = api;
