var api = require("./api"),
    async = require("async"),
    gp = require("geojson-precision"),
    dbgeo = require("dbgeo"),
    larkin = require("./larkin");

module.exports = function(req, res, next) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }
  if (req.query.type === "gmus") {
    larkin.queryPg("earthbase", "SELECT a.gid, a.unit_age, a.rocktype1, a.rocktype2, b.cmin_age, ST_AsGeoJSON(a.the_geom) AS geometry from gmus.geologic_units a JOIN gmus.age b ON a.unit_link = b.unit_link WHERE b.cmin_age = $1", [req.query.interval_name], function(error, result) {
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
    larkin.queryPg("earthbase", "SELECT a.gid, a.rocktype, ST_AsGeoJSON(the_geom) AS geometry, b.interval_name from gmna.geologic_units a JOIN gmna.intervals_old b ON a.eb_interval_id = b.interval_id where b.interval_name = $1", [req.query.interval_name], function(error, result) {
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
