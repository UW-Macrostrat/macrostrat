// Depdendencies for tile server
var tilestrata = require("tilestrata");
var sharp = require("tilestrata-sharp");
var mapnik = require("tilestrata-mapnik");
var dependency = require("tilestrata-dependency");
var cache = require("./cache");

// Depdendencies for tile seeding
var cover = require("tile-cover");
var async = require("async");
var http = require("http");
var pg = require("pg");
var credentials = require("./credentials");
var config = require("./config");
var fs = require("fs");

// Define the tileserver that will be used for cache seedings
var strata = tilestrata.createServer();

// define layers
strata.layer("burwell_tiny")
    .route("tile.png")
        .use(cache({dir: config.cachePath}))
        .use(mapnik({
            xml: config.configPath + "burwell_tiny.xml",
            tileSize: 512,
            scale: 2
        }));

strata.layer("burwell_small")
    .route("tile.png")
        .use(cache({dir: config.cachePath}))
        .use(mapnik({
            xml: config.configPath + "burwell_small.xml",
            tileSize: 512,
            scale: 2
        }));

strata.layer("burwell_medium")
    .route("tile.png")
        .use(cache({dir: config.cachePath}))
        .use(mapnik({
            xml: config.configPath + "burwell_medium.xml",
            tileSize: 512,
            scale: 2
        }));

strata.layer("burwell_large")
    .route("tile.png")
        .use(cache({dir: config.cachePath}))
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

function getBounds(source_id, callback) {
  queryPg("burwell", "SELECT scale FROM maps.sources WHERE source_id = $1", [source_id], function(error, data) {
    if (error || !data.rows || !data.rows.length) {
      return callback(error);
    }

    var scale = data.rows[0].scale

    queryPg("burwell", "SELECT ST_AsGeoJSON(ST_Extent(geom), 4) AS geometry FROM maps." + scale + " WHERE source_id = $1", [source_id], function(error, data) {
      if (error || !data.rows || !data.rows.length) {
        return callback(error);
      }
      callback(data.rows[0].geometry, scale);
    });
  });
}

function clearCache(bbox) {
  deleted = true;
  var zooms = config.scaleMap['large'];

  // Iterate on the zoom levels of the scale 'large'
  async.eachLimit(zooms, 1, function(zoom, callback) {
    console.log('Deleting z', zoom);
    
    // Find all the tiles that cover the bbox of the target source_id
    var coverage = cover.tiles(JSON.parse(bbox), {min_zoom: zoom, max_zoom: zoom});

    // Make sure something legit was returned
    if (coverage.length && coverage.length < 100000) {
      // For each tile, check if it exists and if so delete it
      async.each(coverage, function(tile, tCallback) {
        // Check if it exists
        fs.stat(config.cachePath + '/' + tile[2] + '/' + tile[0] + '/' + tile[1] + '/tile.png', function(error, file) {
          // Doesn't exist
          if (error) {
            return tCallback(null);
          }
          // Exists, delete it
          else {
            fs.unlink(config.cachePath + '/' + tile[2] + '/' + tile[0] + '/' + tile[1] + '/tile.png', function(error) {
              if (error) {
                tCallback(error);
              } else {
                tCallback(null);
              }
            });
          }
        });

      }, function(error) {
        if (error) {
          callback(error);
        } else {
          callback(null);
        }
      });
    } else {
      callback(null);
    }
  }, function(error) {
    if (error) {
      console.log(error);
    }

    console.log('Done deleting tiles');
  });

/*  for (var i = 0; i < zooms.length; i++) {
    var coverage = cover.tiles(JSON.parse(bbox), {min_zoom: zooms[i], max_zoom: zooms[i]});
    if (coverage.length && coverage.length < 100000) {
      console.log('Deleting z' + zooms[i]);
      for (var j = 0; j < coverage.length; j++) {
        try {
          fs.unlinkSync(config.cachePath + '/' + coverage[j][2] + '/' + coverage[j][0] + '/' + tiles[j][1] + '/tile.png');
        } catch(e) {

        }
      }
    }
    console.log('Done deleting z' + zooms[i]);
  }

  console.log('Done deleting tiles')*/
}

console.time("Total");

// Janky
var deleted = false;


try {
  fs.statSync(config.cachePath + '/' + config.scaleMap['large'][0]);
} catch(error) {
  if (error) {
    console.log('Cache path does not exist');
    process.exit();
  }
}

// Seed each of our seedable scales
async.eachLimit(config.seedScales, 1, function(scale, scaleCallback) {
  console.time("Scale");
  console.log("Working on ", scale);

  // These are source-specific additions to land
  var extras;

  var coords = {};

  async.waterfall([
    // Check if a source_id was passed
    function(callback) {
      if (process.argv[2]) {
        // If so, reseed the cache only for that area
        getBounds(process.argv[2], function(bbox, tScale) {

          // Janky in action
          if (!deleted && tScale === 'large') {
            clearCache(bbox);
          }

          // For each zoom level at this scale record the tiles needed to cover the bbox
          async.each(config.scaleMap[scale], function(z, zcallback) {
            coords[z] = [];

            var coverage = cover.tiles(JSON.parse(bbox), {min_zoom: z, max_zoom: z});
            if (coverage.length && coverage.length < 100000) {
              coords[z].push.apply(coords[z], coverage)
              zcallback(null);
            } else {
              zcallback(null);
            }

          }, function(error) {
            callback(null, true);
          });
        });
      } else {
        callback(null, false);
      }
    },


    // Find all the tiles needed to cover land
    function(isSource, callback) {
      // Skip this if a source_id was passed
      if (isSource) {
        return callback(null, isSource);
      }

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
          callback(null, false);
        });
      });
    },

    // Find the bits of sources that exist over water and add that geometry
    function(isSource, callback) {
      // If a source_id was passed skip this step
      if (isSource) {
        return callback(null);
      }

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

    // For each scale, find all tiles that need to be generated
    function(callback) {
      async.eachLimit(config.scaleMap[scale], 1, function(z, zoomCallback) {
        console.time("z");
        console.log("     z", z);

        var newCoords = [];

        // This will be skipped if a source_id is passed
        if (extras && extras.rows) {
          for (var i = 0; i < extras.rows.length; i++) {

            var coverage = cover.tiles(JSON.parse(extras.rows[i].geometry), {min_zoom: z, max_zoom: z});

            if (coverage.length && coverage.length < 200000) {
              for (var q = 0; q < coverage.length; q++) {
                newCoords.push(coverage[q]);
              }
            }
          }
        }


        var allTiles = coords[z].concat(newCoords);

        // Remove duplicates
        var foundTiles = {}
        var unique = allTiles.filter(function(d) {
          if (!foundTiles[d.join(",")]) {
            foundTiles[d.join(",")] = true;
            return d;
          }
        });

        // Once we have a list of tiles, request them (i.e. make GET request, and let tilesever cache save them)
        async.eachLimit(unique, 20, function(tile, tileCallback) {
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
  console.log("Done seeding, waiting for cache");
  console.timeEnd("Total");

  // Wait a minute for the tile cache to catch up before we kill it
  setTimeout(function() {
    process.exit();
  }, 60000);

});
