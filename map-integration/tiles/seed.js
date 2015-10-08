// Depdendencies for tile server
var tilestrata = require("tilestrata");
var disk = require("tilestrata-disk");
var sharp = require("tilestrata-sharp");
var mapnik = require("tilestrata-mapnik");
var dependency = require("tilestrata-dependency");

// Depdendencies for tile seeding
var cover = require("tile-cover");
var async = require("async");
var http = require("http");
var pg = require("pg");
var credentials = require("./credentials");
var config = require("./config");

// Define the tileserver that will be used for cache seedings
var strata = tilestrata.createServer();

// define layers
strata.layer("burwell_tiny")
    .route("tile@2x.png")
        .use(disk.cache({dir: config.cachePath}))
        .use(mapnik({
            xml: config.configPath + "burwell_tiny.xml",
            tileSize: 512,
            scale: 2
        }))
    .route("tile.png")
        .use(disk.cache({dir: config.cachePath}))
        .use(dependency("burwell_tiny", "tile@2x.png"))
        .use(sharp(function(image, sharp) {
            return image.resize(256);
        }));

strata.layer("burwell_small")
    .route("tile.png")
        .use(disk.cache({dir: config.cachePath}))
        .use(mapnik({
            xml: config.configPath + "burwell_small.xml",
            tileSize: 512,
            scale: 2
        }));

strata.layer("burwell_medium")
    .route("tile.png")
        .use(disk.cache({dir: config.cachePath}))
        .use(mapnik({
            xml: config.configPath + "burwell_medium.xml",
            tileSize: 512,
            scale: 2
        }));

strata.layer("burwell_large")
    .route("tile.png")
        .use(disk.cache({dir: config.cachePath}))
        .use(mapnik({
            xml: config.configPath + "burwell_large.xml",
            tileSize: 512,
            scale: 2
        }));

// start accepting requests
strata.listen(config.port);


// Factory for querying PostGIS
function queryPg(db, sql, params, callback) {
  pg.connect("postgres://" + credentials.pg.user + "@" + credentials.pg.host + "/" + db, function(err, client, done) {
    if (err) {
      callback(err);
    } else {
      var query = client.query(sql, params, function(err, result) {
        done();
        if (err) {
          callback(err);
        } else {
          callback(null, result);
        }
      });
    }
  });
}

console.time("Total");
// Seed each of our seedable scales
async.eachLimit(config.seedScales, 1, function(scale, scaleCallback) {
  console.time("Scale");
  console.log("Working on ", scale);

  // These are source-specific additions to land
  var extras;

  var coords = {}

  async.series([
    function(callback) {
      queryPg("burwell", "SELECT ST_AsGeoJSON(geom, 4) AS geometry FROM public.land", [], function(error, data) {
        if (error) {
          console.log(error);
        }

        async.each(config.scaleMap[scale], function(z, zcallback) {
          coords[z] = [];

          async.each(data.rows, function(i, icallback) {
            var coverage = cover.tiles(JSON.parse(i.geometry), {min_zoom: z, max_zoom: z});
            if (coverage.length && coverage.length < 100000) {
              coords[z].push.apply(coords[z], coverage)
              icallback(null);
            } else {
              icallback(null);
            }
          }, function(error) {
            zcallback(null);
          })
        }, function(error) {
          callback(null);
        });
      });
    },

    function(callback) {
      queryPg("burwell", "\
        SELECT ST_AsGeoJSON((ST_Dump(ST_MakeValid(geometry))).geom, 4) geometry FROM ( \
        SELECT ST_Simplify(((st_dump(geom)).geom), 1) AS geometry FROM \
        (SELECT \
          ST_Intersection(ST_GeomFromText('POLYGON ((-179 -85, -179 85, 179 85, 179 -85, -179 -85))', 4326), \
          ST_Difference( \
            (SELECT ST_Buffer(ST_Collect(ref_geom),0) FROM maps.sources WHERE sources.source_id IN (SELECT source_id FROM maps.sources WHERE scale = ANY($1))), \
            (SELECT ST_Buffer(ST_Collect(geom),0) FROM public.land) \
          )) geom \
        ) sub ) foo WHERE geometry is NOT NULL", [config.layerOrder[scale]], function(error, data) {
        if (error) {
          console.log(error);
        }

        extras = data;
        callback(null)
      });
    },

    function(callback) {
      async.eachLimit(config.scaleMap[scale], 1, function(z, zoomCallback) {
        console.time("z");
        console.log("     z", z);

        var newCoords = [];

        for (var i = 0; i < extras.rows.length; i++) {

          var coverage = cover.tiles(JSON.parse(extras.rows[i].geometry), {min_zoom: z, max_zoom: z});

          if (coverage.length && coverage.length < 200000) {
            for (var q = 0; q < coverage.length; q++) {
              newCoords.push(coverage[q]);
            }
          }
        }

        var allTiles = coords[z].concat(newCoords);
        var foundTiles = {}

        var unique = allTiles.filter(function(d) {
          if (!foundTiles[d.join(",")]) {
            foundTiles[d.join(",")] = true;
            return d;
          }
        });

        async.eachLimit(unique, 3, function(tile, tileCallback) {
          http.get("http://localhost:" + config.port + "/burwell_" + scale + "/" + tile[2] + "/" + tile[0] + "/" + tile[1] + "/tile.png", function(res) {
            tileCallback(null);
          });
        }, function(err) {
          if (err) {
            console.log(err);
          }
          console.timeEnd("z");
          zoomCallback(null);

        });
      }, function(err) {
        if (err) {
          console.log(err);
        }
        callback(null);
      });
    }

  ], function(error, result) {
    console.timeEnd("Scale")
    scaleCallback(null);
  });

}, function(error, results) {
  console.log("Done seeding")
  console.timeEnd("Total");
  process.exit();
});
