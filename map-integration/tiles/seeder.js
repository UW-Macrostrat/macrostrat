var fs = require('fs');
var cover = require('tile-cover');
var async = require('async');
var pg = require('pg');
var ProgressBar = require('progress');
var st = require('geojson-bounds');
var mkdirp = require('mkdirp');

var portscanner = require('portscanner');

var config = require('./config');
var makeTile = require('./tileRoller');
var setup = require('./setup');
var credentials = require('./credentials');

var tileSet = '';
// Array of zoom levels we are going to precache
var seedableZooms = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10];

var seedableScales = {
  tiny: config.scaleMap['tiny'],
  small: config.scaleMap['small'],
  medium: config.scaleMap['medium']
};

var zoomLookup = {};
Object.keys(config.scaleMap).forEach(function(scale) {
  config.scaleMap[scale].forEach(function(z) {
    zoomLookup[z] = scale;
  });
});

setTimeout(function() {
  portscanner.checkPortStatus(config.redisPort, '127.0.0.1', function(error, status) {
      if (status === 'open') {
        redis = require('redis');
        client = redis.createClient(config.redisPort, '127.0.0.1', {'return_buffers': true});
      }
  });
}, 10);


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

// Get the envelope for a given source
function getBounds(source_id, callback) {
  queryPg('burwell', 'SELECT scale FROM maps.sources WHERE source_id = $1', [source_id], function(error, data) {
    if (error || !data.rows || !data.rows.length) {
      return callback(error);
    }

    var scale = data.rows[0].scale;

    queryPg('burwell', `
      SELECT ST_AsGeoJSON(
        ST_Intersection(
          ST_GeomFromText('POLYGON ((-179 -85, -179 85, 179 85, 179 -85, -179 -85))', 4326),
          ST_SetSRID(ST_Extent(geom), 4326)
        )
      , 4) AS geometry FROM maps.${scale} WHERE source_id = $1
    `, [source_id], function(error, data) {
      if (error || !data.rows || !data.rows.length) {
        return callback(error);
      }
      callback(data.rows[0].geometry, scale);
    });
  });
}

// Given [minLng, minLat] and [maxLng, maxLat] generate a GeoJSON polygon
function polygonFromMinMax(min, max) {
  return {
    "type": "Polygon",
    "coordinates": [[
      min,
      [min[0], max[1]],
      max,
      [max[0], min[1]],
      min
    ]]
  }
}

/* Because some bounding boxes can be massive, we are always going to split them
   into 16 different boxes, generate a list of tiles, and seed that list one at
   a time. With large bboxes, there were issues generating a list of needed tiles
   because the maximum array length was being reached
*/
function splitExtent(envelope, callback) {
  /*                                        [ext[2], ext[3]]
        -------------------------------------------*
        |          |         |           |         |
  q2    |----------*---------|-----------*---------|  q3
        |          |c2       |           |c3       |
        |--------------------*---------------------|
        |    b     |    c    | c0        |         |
  q1    |----------*---------|-----------*---------|  q4
        |    a     |c1  d    |           |c4       |
        *------------------------------------------
[ext[0], ext[1]]
  */

  // [w, s, e, n]
  var ext = st.extent(envelope);

  // Get center of extent
  var c0 = st.centroid(envelope);

  var q1 = polygonFromMinMax([ext[0], ext[1]], c0);
  var q2 = polygonFromMinMax([ext[0], c0[1]], [c0[0], ext[3]]);
  var q3 = polygonFromMinMax(c0, [ext[2], ext[3]]);
  var q4 = polygonFromMinMax([c0[0], ext[1]], [ext[2], c0[1]]);

  var extents = [];

  async.each([q1, q2, q3, q4], function(q, cb) {
    // Get center
    var _c = st.centroid(q);

    // Get extent
    var extent = st.extent(q);

    var a = polygonFromMinMax([extent[0], extent[1]], _c);
    var b = polygonFromMinMax([extent[0], _c[1]], [_c[0], extent[3]]);
    var c = polygonFromMinMax(_c, [extent[2], extent[3]]);
    var d = polygonFromMinMax([_c[0], extent[1]], [extent[2], _c[1]]);

    extents.push(a, b, c, d);

    cb(null);
  }, function() {
    callback(extents);
  });
}

// Wrapper for tile-cover
function getTileList(geom, z) {
  return cover.tiles(geom, {min_zoom: z, max_zoom: z});
}


function deleteTile(tile, callback) {
  // Check if it exists
  fs.stat(config.cachePath + '/' + tileSet + '/' + tile[2] + '/' + tile[0] + '/' + tile[1] + '/tile.png', function(error, file) {
    // Doesn't exist
    if (error) {
      return callback(null);
    }
    // Exists, delete it
    else {
      fs.unlink(config.cachePath + '/' + tileSet + '/' + tile[2] + '/' + tile[0] + '/' + tile[1] + '/tile.png', function(error) {
        if (error) return callback(error);

        try {
          var redisKey = `${tile[2]},${tile[0]},${tile[1]},${tileSet},tile.png`;
          client.del(redisKey, function(error) {
            return callback(null);
          });
        } catch(er) {
          return callback(null);
        }

      });
    }
  });
}

// Create the tiles
function seed(tiles, showProgress, callback) {
  if (showProgress) {
    var bar = new ProgressBar(':bar :current of :total', { total: tiles.length, width: 50 });
  }

  // Create 20 tiles at a time
  async.eachLimit(tiles, 20, function(tile, tCb) {
    var scale = zoomLookup[tile[2]];


    // Code is in tileRoller.js - uses tilestrata-mapnik/vtile  directly
    createTile(scale, {
      x: tile[0],
      y: tile[1],
      z: tile[2]
    }, function(error) {
      if (showProgress) {
        bar.tick();
      }
      tCb(null);
    });


  }, function() {
    callback(null);
  });
}


function reseed(geometries, scale) {
  async.waterfall([

    // Get the envelope of the geometries
    function(callback) {
      // If reseeding all, just use the provided geometries
      if (scale === '') {
        callback(null, geometries, scale);
      }
      // Otherwise, split the envelope into sections
      else {
        console.log('Splitting extent')
        splitExtent(geometries[0], function(sections) {
          callback(null, sections, scale);
        });
      }
    },

    // If the scale is medium or large, clear the cache
    function(shapes, scale, callback) {
      if (scale && (scale === 'medium' || scale === 'large')) {
        console.log('Clearing large cache');
        async.each(config.scaleMap['large'], function(z, cba) {
          async.each(shapes, function(shape, cbb) {
            async.each(getTileList(shape, z), function(tile, cbc) {
              deleteTile(tile, function() {
                cbc();
              });
            }, function(error) {
                cbb();
            });
          }, function(error) {
              cba();
          });
        }, function(error) {
          console.log('Done deleting large scale tiles');
          callback(null, shapes);
        });
      } else {
        callback(null, shapes);
      }
    },

    // Seed the cache for z0-z6
    function(shapes, callback) {
      console.log('Seeding z0-6');
      var tiles = [];

      // If seeding all, just generate all tiles
      if (scale === '') {
        var polygon = {"type":"Polygon","coordinates":[[[-179,-85],[-179,85],[179,85],[179,-85],[-179,-85]]]};

        var zooms = [0, 1, 2, 3, 4, 5, 6];


        for (var i = 0; i < 7; i++ ) {
          tiles = tiles.concat(getTileList(polygon, i));
        }

      }

      // Otherwise if seeding a source...
      else {
        // Get a list of tiles for each shape at each zoom between 0 and 6
        for (var i = 0; i < shapes.length; i++) {
          for (var z = 0; z < 7; z++) {
            tiles = tiles.concat(getTileList(shapes[i], z));
          }
        }

        // There will be a ton of duplicates, so remove them
        var foundTiles = {};
        tiles = tiles.filter(function(d) {
          if (!foundTiles[d.join('|')]) {
            foundTiles[d.join('|')] = true;
            return d;
          }
        });
      }

      // Actually seed those tiles, then move on
      seed(tiles, true, function() {
        callback(null, shapes);
      });
    },

    // Seed the cache for z7-10
    function(shapes, callback) {
      console.log('Seeding z7-10');

      var zToSeed = seedableZooms.filter(function(d) {
        if (d > 6) {
          return d;
        }
      });

      // Add a progress bar
      var bar = new ProgressBar(':bar :percent', { total: (shapes.length * zToSeed.length), width: 50 });

      // For each section/shape...
      async.eachLimit(shapes, 1, function(shape, cb) {
        // For each seedable zoom level...
        async.each(zToSeed, function(z, cba) {
          async.waterfall([
            // Get a list of tiles
            function(cbb) {
              cbb(null, getTileList(shape, z));
            },

            // Seed that cache
            function(tiles, cbb) {
              seed(tiles, false, function() {
                cbb(null);
              });
            }

          ], function(error) {
            // Done with z for shape
            bar.tick();
            cba();
          });
        }, function(error) {
          // Done with shape
          cb();
        });
      }, function(error) {
        // Done with all shapes
        callback();
      });

    }], function() {
      // Done with all shapes
      console.log('Done seeding');
      process.exit();
    });
}


function reseedAll() {
  console.log('Getting geometry to seed');

  // Crop everything to (-179 -85), (179, 85)
  async.waterfall([
    // Get land
    function(callback) {
      queryPg('burwell', `
        SELECT ST_AsGeoJSON(
          ST_Intersection(
              ST_GeomFromText('POLYGON ((-179 -85, -179 85, 179 85, 179 -85, -179 -85))', 4326),
              ST_Union(rgeom)
            )
        , 4) AS geometry
        FROM maps.sources
      `, [], function(error, data) {
        if (error) {
          console.log(error);
        }

        var lands = data.rows.map(function(d) { return JSON.parse(d.geometry); });

        callback(null, lands);
      });
    }
  ], function(error, lands) {
    reseed(lands, '');
  });
}



function reseedSource(source_id) {
  console.log('Getting bounds for source_id ', source_id);
  getBounds(source_id, function(bbox, scale) {
    reseed([JSON.parse(bbox)], scale);
  });
}

function validateSource(source_id, callback) {
  queryPg("burwell", "SELECT source_id FROM maps.sources WHERE source_id = $1", [source_id], function(error, result) {
    if (error) return callback(error);
    if (result.rows && result.rows.length === 1) {
      callback(null, true);
    } else {
      callback(null, false);
    }
  });
}

function getScaleSources(scale, callback) {
  queryPg("burwell", "SELECT source_id FROM maps.sources WHERE scale = $1", [scale], function(error, result) {
    if (error) return callback(error);
    var sources = result.rows.map(function(d) { return d.source_id; });
    callback(null, sources);
  });
}

module.exports = function(params) {
  async.series([
    function(callback) {
      tileSet = params.tileSet;
      // Make sure cachePaths exists
      if (params.tileType === 'raster') {
        mkdirp(config.cachePath + '/' + params.tileSet, function(error) {
          if (error) return callback(error);
          callback();
        })
      } else {
        mkdirp(config.cachePathVector + '/', function(error) {
          if (error) return callback(error);

          callback();
        })
      }
    },

    // Set up the project files (Mapnik XML) (not necessary for vector tiles as they are unstyled)
    function(callback) {
      if (params.tileType === 'raster') {
        setup(params.tileSet, function(error) {
          if (error) {
            console.log('An error occurred while creating configuration files');
            callback(error);
          } else {
            console.log('Configuration files generated');
            callback(null);
          }
        });
      } else {
        callback(null)
      }
    },

    // Initialize the tile providers
    function(callback) {
      makeTile.init(params.tileSet, params.tileType, function() {
        console.log('Tile providers initialized');
        callback();
      });
    }
  ], function(error) {
    if (error) {
      process.exit(1);
    }

    createTile = (params.tileType === 'vector') ? makeTile.roll.vector : makeTile.roll.raster;

    switch (params.target) {
      case 'all':
        reseedAll();
        break;
      case 'source':
      case 'scale':
        params.source_id.forEach(function(d) {
          reseedSource(d);
        });
        break;
      default:
        console.log('QUITTING - no valid operation passed')
    }

  });

}

module.exports.validateSource = validateSource;
module.exports.getScaleSources = getScaleSources;
