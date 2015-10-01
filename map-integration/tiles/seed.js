// Depdendencies for tile server
var tilestrata = require('tilestrata');
var disk = require('tilestrata-disk');
var sharp = require('tilestrata-sharp');
var mapnik = require('tilestrata-mapnik');
var dependency = require('tilestrata-dependency');

// Depdendencies for tile seeding
var cover = require("tile-cover");
var async = require("async");
var http = require("http");
var pg = require("pg");
var credentials = require("./credentials");

var strata = tilestrata.createServer();


// define layers
strata.layer('burwell_tiny')
    .route('tile@2x.png')
        .use(disk.cache({dir: credentials.settings.cachePath}))
        .use(mapnik({
            xml: credentials.settings.configPath + 'burwell_tiny.xml',
            tileSize: 512,
            scale: 2
        }))
    .route('tile.png')
        .use(disk.cache({dir: credentials.settings.cachePath}))
        .use(dependency('burwell_tiny', 'tile@2x.png'))
        .use(sharp(function(image, sharp) {
            return image.resize(256);
        }));

strata.layer('burwell_small')
    .route('tile.png')
        .use(disk.cache({dir: credentials.settings.cachePath}))
        .use(mapnik({
            xml: credentials.settings.configPath + 'burwell_small.xml',
            tileSize: 512,
            scale: 2
        }));

strata.layer('burwell_medium')
    .route('tile.png')
        .use(disk.cache({dir: credentials.settings.cachePath}))
        .use(mapnik({
            xml: credentials.settings.configPath + 'burwell_medium.xml',
            tileSize: 512,
            scale: 2
        }));

strata.layer('burwell_large')
    .route('tile.png')
        .use(disk.cache({dir: credentials.settings.cachePath}))
        .use(mapnik({
            xml: credentials.settings.configPath + 'burwell_large.xml',
            tileSize: 512,
            scale: 2
        }));

// start accepting requests
strata.listen(credentials.settings.port);


function queryPg(db, sql, params, callback, send, res, format, next) {
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

var scaleHash = {
  "tiny": [0, 1, 2, 3],
  "small": [4, 5],
  "medium": [6, 7, 8, 9, 10],
  "large": [11, 12, 13]
}


var scaleGroups = {
  "tiny": ["tiny"],
  "small": ["tiny", "large", "medium", "small"],
  "medium": ["large", "small", "medium"],
  "large": ["medium", "large"]
}

//var scales = ["tiny", "small", "medium", "large"];
var scales = ["tiny", "small"];

async.eachLimit(scales, 1, function(scale, scaleCallback) {
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

        async.each(scaleHash[scale], function(z, zcallback) {
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
        ) sub ) foo WHERE geometry is NOT NULL", [scaleGroups[scale]], function(error, data) {
        if (error) {
          console.log(error);
        }

        extras = data;
        callback(null)
      });
    },

    function(callback) {
      async.eachLimit(scaleHash[scale], 1, function(z, zoomCallback) {
        console.log("     z", z);

        var newCoords = [];

        for (var i = 0; i < extras.rows.length; i++) {
          //console.log(i, extras.rows[i].geometry)
          var coverage = cover.tiles(JSON.parse(extras.rows[i].geometry), {min_zoom: z, max_zoom: z});
        //  console.log(i, extras.rows[i].geometry.length, coverage.length);

          if (coverage.length && coverage.length < 100000) {
            for (var q = 0; q < coverage.length; q++) {
            //  console.log(q, coverage[q]);
              newCoords.push(coverage[q]);
            }
          }
          //newCoords.push.apply(newCoords, (cover.tiles(JSON.parse(extras.rows[i].geometry), {min_zoom: z, max_zoom: z})));
        }
        //console.log(z, coords[z].length)

        var allTiles = coords[z].concat(newCoords);
        var foundTiles = {}

        var unique = allTiles.filter(function(d) {
          if (!foundTiles[d.join(',')]) {
            foundTiles[d.join(',')] = true;
            return d;
          }
        });

        async.eachLimit(unique, 10, function(tile, tileCallback) {
          http.get('http://localhost:' + credentials.settings.port + '/burwell_' + scale + '/' + tile[2] + '/' + tile[0] + '/' + tile[1] + '/tile.png', function(res) {
            tileCallback(null);
          });
        }, function(err) {
          if (err) {
            console.log(err);
          }
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
    scaleCallback(null);
  });

}, function(error, results) {
  console.log("Done seeding")
  process.exit();
});
