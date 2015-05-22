var api = require("./api"),
    async = require("async"),
    gp = require("geojson-precision"),
    dbgeo = require("dbgeo"),
    larkin = require("./larkin");

module.exports = function(req, res, next) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }
  // Require both a map type and interval name
  if (!req.query.type || !req.query.interval_name) {
    return larkin.error(req, res, next, "A map type and interval name are required");
  }

  if (req.query.type === "gmus") {
    // Find age range of requested interval, and then use that to query age_bottom and age_top
    larkin.queryPg("geomacro", "WITH range AS (SELECT age_bottom, age_top FROM macrostrat.intervals WHERE interval_name = $1) SELECT gid, unit_age, rocktype1, rocktype2, min_interval_name AS cmin_age, ST_AsGeoJSON(geom) AS geometry FROM gmus.lookup_units WHERE age_bottom <= (select age_bottom from range) AND age_top >= (select age_top from range)", [req.query.interval_name], function(error, result) {
      dbgeo.parse({
        "data": result.rows,
        "outputFormat": larkin.getOutputFormat(req.query.format),
        "callback": function(error, result) {
          if (error) {
            larkin.error(req, res, next, error);
          } else {
            if (larkin.getOutputFormat(req.query.format) === "geojson") {
              result = gp(result, 6);
            }
            if (api.acceptedFormats.bare[req.query.format]) {
              larkin.sendBare(result, res, next);
            } else {
              larkin.sendCompact(result, res, null, next);
            }
          }
        }
      });
    });
  } else if (req.query.type === "gmna") {
    larkin.queryPg("geomacro", "WITH range AS (SELECT age_bottom, age_top FROM macrostrat.intervals WHERE interval_name = $1) SELECT gid, rocktype, ST_AsGeoJSON(geom) AS geometry FROM gmna.lookup_units WHERE max_age <= (select age_bottom from range) AND min_age >= (select age_top from range)", [req.query.interval_name], function(error, result) {
      dbgeo.parse({
        "data": result.rows,
        "outputFormat": larkin.getOutputFormat(req.query.format),
        "callback": function(error, result) {
          if (error) {
            larkin.error(req, res, next, error);
          } else {
            if (larkin.getOutputFormat(req.query.format) === "geojson") {
              result = gp(result, 6);
            }
            if (api.acceptedFormats.bare[req.query.format]) {
              larkin.sendBare(result, res, next);
            } else {
              larkin.sendCompact(result, res, null, next);
            }
          }
        }
      });
    });
  } else {
    larkin.error(req, res, next, "Invalid parameters");
  }
}
