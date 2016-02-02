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
var path = require('path');
var st = require('geojson-bounds');
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

var zoomLookup = {};
Object.keys(config.scaleMap).forEach(function(scale) {
  config.scaleMap[scale].forEach(function(z) {
    zoomLookup[z] = scale;
  });
});

// Define the tileserver that will be used for cache seedings
var strata = tilestrata();

// define layers
strata.layer('burwell_tiny')
    .route('tile.png')
        .use(cache({dir: config.cachePath}))
        .use(mapnik({
            pathname: config.configPath + 'burwell_tiny.xml',
            tileSize: 512,
            scale: 2
        }));

strata.layer('burwell_small')
    .route('tile.png')
        .use(cache({dir: config.cachePath}))
        .use(mapnik({
            pathname: config.configPath + 'burwell_small.xml',
            tileSize: 512,
            scale: 2
        }));

strata.layer('burwell_medium')
    .route('tile.png')
        .use(cache({dir: config.cachePath}))
        .use(mapnik({
            pathname: config.configPath + 'burwell_medium.xml',
            tileSize: 512,
            scale: 2
        }));

strata.layer('burwell_large')
    .route('tile.png')
        .use(cache({dir: config.cachePath}))
        .use(mapnik({
            pathname: config.configPath + 'burwell_large.xml',
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

    var scale = data.rows[0].scale;

    queryPg('burwell', 'SELECT ST_AsGeoJSON(ST_Extent(geom), 4) AS geometry FROM maps.' + scale + ' WHERE source_id = $1', [source_id], function(error, data) {
      if (error || !data.rows || !data.rows.length) {
        return callback(error);
      }
      callback(data.rows[0].geometry, scale);
    });
  });
}

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


function getTileList(geom, z) {
  return cover.tiles(geom, {min_zoom: z, max_zoom: z});
}


function deleteTile(tile, callback) {
  // Check if it exists
  fs.stat(config.cachePath + '/' + tile[2] + '/' + tile[0] + '/' + tile[1] + '/tile.png', function(error, file) {
    // Doesn't exist
    if (error) {
      return callback(null);
    }
    // Exists, delete it
    else {
      fs.unlink(config.cachePath + '/' + tile[2] + '/' + tile[0] + '/' + tile[1] + '/tile.png', function(error) {
        if (error) {
          callback(error);
        } else {
          callback(null);
        }
      });
    }
  });
}


function seed(tiles, callback) {
  var t = 1;

  async.eachLimit(tiles, 20, function(tile, tCb) {

    var scale = zoomLookup[tile[2]];

    http.get({
      host: `localhost`,
      port: `${config.port}`,
      path: `/burwell_${scale}/${tile[2]}/${tile[0]}/${tile[1]}/tile.png`
    }, function(res) {
      process.stdout.write('   ' + t + ' of ' + tiles.length + (t != tiles.length ? '\r' : '\n'));
      t++;
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

      for (var i = 0; i < shapes.length; i++) {
        for (var z = 0; z < 7; z++) {
          tiles.push(getTileList(shapes[i], z)[0]);
        }
      }

      var foundTiles = {};
      tiles = tiles.filter(function(d) {
        if (!foundTiles[d.join('|')]) {
          foundTiles[d.join('|')] = true;
          return d;
        }
      });

      seed(tiles, function() {
        callback(null, shapes);
      });
    },

    // Seed the cache
    function(shapes, callback) {
      console.log('Seeding z7-10');
      var zToSeed = seedableZooms.filter(function(d) {
        if (d > 6) {
          return d;
        }
      });

      var seeded = 1;
      // For each section/shape...
      async.eachLimit(shapes, 3, function(shape, cb) {
        // For each seedable zoom level...
        async.each(zToSeed, function(z, cba) {

          async.waterfall([
            // Get a list of tiles
            function(cbb) {
              cbb(null, getTileList(shape, z));
            },

            // Seed that cache
            function(tiles, cbb) {
              seed(tiles, function() {
                cbb(null);
              });
            }

          ], function(error) {
            cba();
          });
        }, function(error) {
          process.stdout.write('            Done seeding shape ' + seeded + ' of ' + shapes.length + '\r')
          seeded += 1;
          cb();
        });
      }, function(error) {

        callback();
      });

    }], function() {
      console.log('Done seeding, waiting for cache');

      // Wait a minute for the tile cache to catch up before we kill it
      setTimeout(function() {
        process.exit();
      }, 60000);

    });
}


function reseedAll() {
  // Skip the BS and just use ST_GeomFromText('POLYGON ((-179 -85, -179 85, 179 85, 179 -85, -179 -85))', 4326)
  console.log('Getting geometry to seed');
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

    reseed([].concat(lands, water), '');
  });
}



function reseedSource(source_id) {
  console.log('Getting bounds for source_id ', source_id);
  getBounds(source_id, function(bbox, scale) {
    reseed([JSON.parse(bbox)], scale);
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

setTimeout(function() {
  if (process.argv[2]) {
    reseedSource(process.argv[2]);
  } else {
    reseedAll();
  }
}, 3000);
