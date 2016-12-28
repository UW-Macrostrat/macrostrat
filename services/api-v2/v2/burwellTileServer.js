var tilestrata = require("tilestrata");
var mapnik = require("tilestrata-mapnik");
var headers = require("tilestrata-headers");
var etag = require("tilestrata-etag");
var vtile = require("tilestrata-vtile");
var portscanner = require("portscanner");
var credentials = require("./credentials");

module.exports = tilestrata.middleware({
  prefix: "/maps/burwell",
  server: (function() {
    var strata = tilestrata();


    // Create a provider for all active tile layers
    credentials.tiles.activeLayers.forEach(function(layer) {
      strata.layer(layer)
          .route("tile.png")
          .use(mapnik({
              xml: credentials.tiles.configPath + `/burwell_large_${layer}.xml`,
              tileSize: 512,
              scale: 2
          }))
          .use(headers({
            "Cache-Control": "max-age=604800",
            "X-Powered-By": "TileStrata"
          }))
          .use(etag())
          // 
          // .route('tile.pbf')
          //     .use(vtile({
          //         xml: credentials.tiles.configPath + `/burwell_vector_large_${layer}.xml`,
          //         tileSize: 256,
          //         metatile: 1,
          //         bufferSize: 128
          //     }))
          //     .use(etag())
    });

    // Check if Redis is running
    setTimeout(function() {
      portscanner.checkPortStatus(credentials.redis.port, "127.0.0.1", function(error, status) {
        if (status === "open") {
          var cache = require("./redisCache");
          console.log("Using Redis cache for tiles")
        } else {
          var cache = require("./customCache");
          console.log("Using application cache for tiles");
        }

        // Initialize a cache for each active tile layer
        credentials.tiles.activeLayers.forEach(function(layer) {
          strata.layer(layer)
              .route("tile.png")
                  .use(cache({
                    size: "1GB", // only for application cache
                    ttl: 3000,
                    lruMaxAge: 21600000,  // 6hrs
                    diskMaxAge: 86400000, // 24hrs
                    dir: credentials.tiles.stashPath + '/' + layer,
                    defaultTile: __dirname + "/default@2x.png"
                  }));
        });
      });

    }, 10)

    return strata;

  }())
});
