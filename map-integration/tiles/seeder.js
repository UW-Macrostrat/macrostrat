// Depdendencies for tile server
var tilestrata = require('tilestrata');
var sharp = require('tilestrata-sharp');
var mapnik = require('tilestrata-mapnik');
var dependency = require('tilestrata-dependency');
var cache = require('./cache');

// Depdendencies for tile seeding
var cover = require('tile-cover');
var async = require('async');
var http = require('http');
var fs = require('fs');
var ProgressBar = require('progress');
var config = require('./config');
var pg = require('pg');
var credentials = require('./credentials');

// Array of zoom levels we are going to precache
var seedableZooms = [].concat(config.scaleMap['tiny'], config.scaleMap['small'], config.scaleMap['medium']);

var seedableScales = {
  tiny: config.scaleMap['tiny'],
  small: config.scaleMap['small'],
  medium: config.scaleMap['medium']
};


// Define the tileserver that will be used for cache seedings
var strata = tilestrata.createServer();

// define layers
strata.layer('burwell_tiny')
    .route('tile.png')
        .use(cache({dir: config.cachePath}))
        .use(mapnik({
            xml: config.configPath + 'burwell_tiny.xml',
            tileSize: 512,
            scale: 2
        }));

strata.layer('burwell_small')
    .route('tile.png')
        .use(cache({dir: config.cachePath}))
        .use(mapnik({
            xml: config.configPath + 'burwell_small.xml',
            tileSize: 512,
            scale: 2
        }));

strata.layer('burwell_medium')
    .route('tile.png')
        .use(cache({dir: config.cachePath}))
        .use(mapnik({
            xml: config.configPath + 'burwell_medium.xml',
            tileSize: 512,
            scale: 2
        }));

strata.layer('burwell_large')
    .route('tile.png')
        .use(cache({dir: config.cachePath}))
        .use(mapnik({
            xml: config.configPath + 'burwell_large.xml',
            tileSize: 512,
            scale: 2
        }));

// start accepting requests
strata.listen(config.port);


// Factory for querying PostGIS
function queryPg(db, sql, params, callback) {
  pg.connect('postgres://' + credentials.pg.user + '@' + credentials.pg.host + '/' + db, function(err, client, done) {
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
  queryPg('burwell', 'SELECT scale FROM maps.sources WHERE source_id = $1', [source_id], function(error, data) {
    if (error || !data.rows || !data.rows.length) {
      return callback(error);
    }

    queryPg('burwell', 'SELECT ST_AsGeoJSON(ST_Extent(geom), 4) AS geometry FROM maps.' + data.rows[0].scale + ' WHERE source_id = $1', [source_id], function(error, data) {
      if (error || !data.rows || !data.rows.length) {
        return callback(error);
      }
      callback(data.rows[0].geometry, data.rows[0].scale);
    });
  });
}


function reseed(geometries, all) {
  async.waterfall([
    // delete the large scale cache
    function(callback) {
      // if reseeding all, simply delete all existing tiles
      if (all) {
        fs.readdirSync(config.cachePath)
          .filter(function(file) {
            return fs.statSync(path.join(config.cachePath, file)).isDirectory();
          })
          .forEach(function(zoomDirectory) {
            fs.unlink(path.join(config.cachePath, zoomDirectory));
          });
      } else {
      /*  async.each(geometries, function(geom, geomCb) {
          // Iterate on the zoom levels of the scale 'large'
          async.eachLimit(config.scaleMap['large'], 1, function(zoom, zCb) {

            // Find all the tiles that cover the bbox of the target source_id
            var coverage = cover.tiles(geom, {min_zoom: zoom, max_zoom: zoom});

            // Make sure something legit was returned
            if (coverage.length && coverage.length < 100000) {
              // For each tile, check if it exists and if so delete it
              async.each(coverage, function(tile, tCb) {
                // Check if it exists
                fs.stat(config.cachePath + '/' + tile[2] + '/' + tile[0] + '/' + tile[1] + '/tile.png', function(error, file) {
                  // Doesn't exist
                  if (error) {
                    return tCb(null);
                  }
                  // Exists, delete it
                  else {
                    fs.unlink(config.cachePath + '/' + tile[2] + '/' + tile[0] + '/' + tile[1] + '/tile.png', function(error) {
                      if (error) {
                        tCb(error);
                      } else {
                        tCb(null);
                      }
                    });
                  }
                });

              }, function(error) {
                if (error) {
                  zCb(error);
                } else {
                  zCb(null);
                }
              });
            } else {
              zCb(null);
            }
          }, function(error) {
            if (error) {
              console.log(error);
            }

            geomCb();
          });
        }, function() {
          console.log('Done deleting tiles')
          callback(null);
        });*/
      }

    },

    // Get tile list
    function(callback) {
      // Generate a list of tiles
      var tilesToSeed = {};

      // For each geometry, and each zoom level, get the needed tiles
      async.each(geometries, function(geom, geomCb) {
        async.each(Object.keys(seedableScales), function(scale, sCb) {
          if (!tilesToSeed[scale]) {
            tilesToSeed[scale] = [];
          }
          async.each(config.scaleMap[scale], function(z, zCb) {
            var coverage = cover.tiles(geom, {min_zoom: z, max_zoom: z});
            if (coverage.length && coverage.length < 100000) {
              tilesToSeed[scale].push.apply(tilesToSeed[scale], coverage);
              zCb(null);
            } else {
              zCb(null);
            }
          }, function() {
            sCb(null);
          });
        }, function() {
          geomCb(null);
        });
      }, function(err) {

        // Remove duplicate tiles
        var foundTiles = {};

        Object.keys(tilesToSeed).forEach(function(scale) {
          tilesToSeed[scale] = tilesToSeed[scale].filter(function(tile) {
            if (!foundTiles[tile.join('|')]) {
              foundTiles[tile.join('|')] = true;
              return tile;
            }
          });
        });

        callback(null, tilesToSeed);

      });
    },

    // Fetch the tiles
    function(tiles, callback) {
      async.eachLimit(Object.keys(tiles), 1, function(scale, sCb) {
        // Make a progress bar
        console.log('Caching ' + scale);
        var bar = new ProgressBar(':bar :current of :total (:percent) Total: :elapsed(s)', { total: tiles[scale].length, width: 30 });

        async.eachLimit(tiles[scale], 20, function(tile, tCb) {
          http.get(`http://localhost:${config.port}/burwell_${scale}/${tile[2]}/${tile[0]}/${tile[1]}/tile.png`, function(res) {
            bar.tick();
            tCb();
          })
        }, function() {
          sCb(null);
        });
      }, function() {
        callback(null);
      });
    }

  ], function() {
    console.log('Done seeding, waiting for cache');

    // Wait a minute for the tile cache to catch up before we kill it
    setTimeout(function() {
      process.exit();
    }, 60000);

  });

}


function reseedAll() {
  async.waterfall([
    // Get land
    function(callback) {
      queryPg('burwell', 'SELECT ST_AsGeoJSON(geom, 4) AS geometry FROM public.land', [], function(error, data) {
        if (error) {
          console.log(error);
        }

        var lands = data.rows.map(function(d) { return JSON.parse(d.geometry); });

        callback(null, lands);
      });
    },

    // Get water
    function(lands, callback) {
      queryPg('burwell', `
        SELECT ST_AsGeoJSON((ST_Dump(ST_MakeValid(geometry))).geom, 4) geometry FROM (
          SELECT ST_Simplify(((st_dump(geom)).geom), 1) AS geometry FROM (
          SELECT
            ST_Intersection(
              ST_GeomFromText('POLYGON ((-179 -85, -179 85, 179 85, 179 -85, -179 -85))', 4326),
              ST_Difference(
                (SELECT ST_Buffer(ST_Collect(ref_geom),0) FROM maps.sources),
                (SELECT ST_Buffer(ST_Collect(geom),0) FROM public.land)
              )
            ) geom
          ) sub
        ) foo
        WHERE geometry is NOT NULL
      `, [], function(error, data) {
        if (error) {
          console.log(error);
        }

        var water = data.rows.map(function(d) { return JSON.parse(d.geometry); });

        callback(null, lands, water);
      });
    }
  ], function(error, lands, water) {

    reseed([].concat(lands, water), true);
  });
}



function reseedSource() {
  getBounds(process.argv[2], function(bbox, scale) {
    reseed([JSON.parse(bbox)], false, scale);
  });
}


// Make sure cachePath exists
try {
  fs.statSync(config.cachePath);
} catch(error) {
  if (error) {
    console.log('Cache path does not exist', config.cachePath, error);
    process.exit();
  }
}

if (process.argv[2]) {
  reseedSource(process.argv[2]);
} else {
  reseedAll();
}
