var express = require("express");
var tilestrata = require("tilestrata");
var mapnik = require("tilestrata-mapnik");
var dependency = require("tilestrata-dependency");
var credentials = require("./credentials");
var portscanner = require("portscanner");

var api = express.Router();

api.use(function(req, res, next) {
  res.header("Access-Control-Allow-Origin", "*");
  res.header("Access-Control-Allow-Headers", "Origin, X-Requested-With, Content-Type, Accept");
  res.header("Access-Control-Allow-Methods", "GET, POST, PUT, OPTIONS");
  next();
});

// Set up the tileserver
api.use(tilestrata.middleware({
  server: (function() {
    var strata = tilestrata();

    strata.layer("burwell")
        .route("tile.png")
        .use(mapnik({
            xml: credentials.tiles.config,
            tileSize: 512,
            scale: 2
        }));

    // Check if Redis is running
    setTimeout(function() {
      portscanner.checkPortStatus(6379, "127.0.0.1", function(error, status) {
        if (status === "open") {
          var cache = require("./redisCache");
          console.log("Using Redis cache for tiles")
        } else {
          var cache = require("./customCache");
          console.log("Using application cache for tiles");
        }

        strata.layer("burwell")
            .route("tile.png")
                .use(cache({
                  size: "2GB", // only for application cache
                  ttl: 3000,
                  lruMaxAge: 21600000,  // 6hrs
                  diskMaxAge: 86400000, // 24hrs
                  dir: credentials.tiles.path,
                  defaultTile: __dirname + "/default@2x.png"
                }));
      });

    }, 10)

    return strata;

  }()),
  prefix: "/maps"
}));


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
