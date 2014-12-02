var api = require("./api"),
    async = require("async"),
    dbgeo = require("dbgeo"),
    larkin = require("./larkin");

module.exports = function(req, res, next) {
  if (!req.query.age && !req.query.interval_name) {
    larkin.info(req, res, next);
  } else {
    async.waterfall([
      function(callback) {
        if (req.query.age) {
          callback(null, req.query.age);
        } else if (req.query.interval_name) {
          larkin.query("SELECT (age_bottom + age_top)/2 AS mid FROM intervals WHERE interval_name = ?", [req.query.interval_name], function(error, result) {
            if (error) {
              callback(error);
            } else {
              if (result.length === 1) {
                callback(null, parseInt(result[0].mid));
              } else {
                larkin.error(req, res, next, "interval not found");
              }
            }
          });
        }
      },
      function(year, callback) {
        larkin.queryPg("alice", "SELECT plateid::integer, ST_AsGeoJSON(geom) AS geometry FROM merge.reconstructed_" + year + "_merged", [], function(error, result) {
          callback(null, result.rows);
        });
      }
    ], function(error, data) {
      if (error) {
        larkin.error(req, res, next, "Something went wrong");
      } else {
        dbgeo.parse({
          "data": data,
          "outputFormat": larkin.getOutputFormat(req.query.format),
          "callback": function(error, result) {
            if (error) {
              larkin.error(req, res, next, "Something went wrong");
            } else {
              if (req.query.format && api.acceptedFormats.bare[req.query.format]) {
                larkin.sendBare(result, res, next);
              } else {
                larkin.sendData(result, res, null, next);
              }
            }
          }
        });
      }
    });
  }
}
