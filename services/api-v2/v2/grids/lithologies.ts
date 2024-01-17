var api = require("../api"),
    larkin = require("../larkin"),
    grid = require("brute-force-equal-area"),
    crypto = require("crypto"),
    dbgeo = require("dbgeo"),
    async = require("async");

// via http://blog.tompawlak.org/how-to-generate-random-values-nodejs-javascript
function randomString() {
    var chars = "abcdefghijklmnopqrstuwxyzABCDEFGHIJKLMNOPQRSTUWXYZ0123456789";
    var rnd = crypto.randomBytes(10),
        value = new Array(10),
        len = chars.length;

    for (var i = 0; i < 10; i++) {
        value[i] = chars[rnd[i] % len];
    }

    return value.join('');
}


module.exports = function(req, res, next) {
  if (!req.query || !req.query.lngSpacing || !req.query.latSpacing) {
    return larkin.info(req, res, next);
  }

  var origin = (req.query.orginLat && req.query.originLng) ? [req.query.originLng, req.query.originLat] : [0,0];

  async.waterfall([
    // Create grid using parameters
    function(callback) {
      console.log('step 1 - create grid');
      grid.variable(parseFloat(req.query.lngSpacing), parseFloat(req.query.latSpacing), origin, function(geojson) {
        callback(null, geojson);
      });
    },

    // Create table
    function(grid, callback) {
      console.log('step 2 - create table');
      // Create a unique hash key
      var table = randomString();

      larkin.queryPg("burwell", "CREATE TABLE " + table + " (id integer, geom geometry)", [], function(error) {
        if (error) {
          callback(error);
        }
        callback(null, grid, table);
      });
    },

    // Insert geojson
    function(grid, table, callback) {
      console.log('step 3 - insert geojson');
      async.eachLimit(grid.features, 10, function(cell, callback) {
        cell.geometry.crs = {"type": "name", "properties": {"name": "EPSG:4326"}};

        larkin.queryPg("burwell", "INSERT INTO " + table + " (id, geom) VALUES ($1, ST_GeomFromGeoJSON($2))", [cell.properties.id, cell.geometry], function(error) {
          if (error) {
            callback(error);
          }
          callback(null);
        })
      }, function(error) {
        if (error) {
          callback(error);
        }
        callback(null, table);
      });
    },

    // Create spatial index on temp table
    function(table, callback) {
      console.log('step 3.5 - spatially index temp table');
      larkin.queryPg("burwell", "CREATE INDEX ON " + table + " USING GiST (geom)", [], function(error) {
        callback(null, table);
      });
    },

    // Update the table with lithologies
    function(table, callback) {
      console.log('step 4 - update table with lithologies');
    },

    // Select the geojson cells that intersect the envelope of the target dataset
    function(table, callback) {
      larkin.queryPg("burwell", "SELECT id, ST_AsGeoJSON(geom) AS geometry FROM " + table, [], function(error, result) {
        if (error) {
          callback(error);
        }
        dbgeo.parse({
          "outputFormat": larkin.getOutputFormat(req.query.format),
          "data": result.rows
        }, function(error, geojson) {
          if (error) {
            callback(error);
          }
          callback(null, geojson, table);
        });
      });
    },

    // Drop the temp table
    function(grid, table, callback) {
      larkin.queryPg("burwell", "DROP TABLE " + table, [], function(error) {
        callback(null, grid);
      });
    }

  ],

  // return geo/topojson or error
  function(error, result) {
    if (error) {
      console.log(error);
    }

    larkin.sendData(req, res, next, {
      format: (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json",
      bare: (api.acceptedFormats.bare[req.query.format]) ? true : false
    }, {
      data: result
    });
  });

}
