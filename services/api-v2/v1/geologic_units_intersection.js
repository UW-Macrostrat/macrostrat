var api = require("./api"),
    dbgeo = require("dbgeo"),
    gp = require("geojson-precision"),
    larkin = require("./larkin");

module.exports = function(req, res, next) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }
  if (!(req.query.line || req.query.shape) || !req.query.type) {
    return larkin.error(req, res, next, "A valid WKT shape and map type are required");
  }

  var type = (["gmna", "gmus"].indexOf(req.query.type) > -1) ? req.query.type : "gmna",
      buffer = (req.query.buffer && !isNaN(parseInt(req.query.buffer))) ? parseInt(req.query.buffer)*1000 : 35000,
      shape = (req.query.line) ? req.query.line : req.query.shape;

  if (type === "gmna") {
    larkin.queryPg("geomacro", "WITH linestring AS (SELECT ST_Buffer(ST_SnapToGrid($1::geometry, 0.1)::geography, $2) AS buffer) SELECT gid AS id, unit_abbre, rocktype, lithology AS lith, min_age, max_age, interval_color AS color, ST_AsGeoJSON(ST_Intersection(geom, buffer)) AS geometry FROM gmna.lookup_units, linestring WHERE ST_Intersects(geom, buffer) is true", [shape, buffer], function(error, result) {
      if (error) {
        larkin.error(req, res, next, "Something went wrong");
      } else {
        dbgeo.parse({
          "data": result.rows,
          "outputFormat": larkin.getOutputFormat(req.query.format),
          "callback": function(error, result) {
            if (error) {
              larkin.error(req, res, next, "Something went wrong");
            } else {
              if (larkin.getOutputFormat(req.query.format) === "geojson") {
                result = gp(result, 4);
              }
              if (api.acceptedFormats.bare[req.query.format]) {
                larkin.sendBare(result, res, next);
              } else {
                larkin.sendCompact(result, res, null, next);
              }
            }
          }
        });
      }
    });
  } else {
    larkin.queryPg("geomacro", "SELECT ST_Area(ST_Buffer($1::geography, $2))/100000000 AS area", [shape, buffer], function(err, data) {
      if (err) {
        return larkin.error(req, res, next, "Invalid geometry supplied");
      }
      if (data.rows[0].area > 1000) {
        return larkin.error(req, res, next, "Area too large. Please select a smaller area.");
      } else {
        larkin.queryPg("geomacro", "WITH linestring AS (SELECT ST_Buffer(ST_SnapToGrid($1::geometry, 0.1)::geography, $2) AS buffer), states as (SELECT postal FROM us_states WHERE ST_Intersects(geom::geography, (SELECT buffer FROM linestring))), subset as (SELECT * FROM gmus.lookup_units WHERE upper(state) in (SELECT postal FROM states)) SELECT gid AS id, state, rocktype1, rocktype2, u_rocktype3 AS rocktype3, unit_name, unit_age, unitdesc, strat_unit, unit_com, interval_color AS color, ST_AsGeoJSON(ST_Intersection(geom, buffer)) AS geometry FROM subset, linestring WHERE ST_Intersects(geom::geography, buffer) is true", [shape, buffer], function(error, result) {
          if (error) {
            larkin.error(req, res, next, "Something went wrong");
          } else {
            dbgeo.parse({
              "data": result.rows,
              "outputFormat": (req.query.format) ? larkin.getOutputFormat(req.query.format) : "geojson",
              "callback": function(error, result) {
                if (error) {
                  larkin.error(req, res, next, "Something went wrong");
                } else {
                  if (larkin.getOutputFormat(req.query.format) === "geojson") {
                    result = gp(result, 4);
                  }
                  if (api.acceptedFormats.bare[req.query.format]) {
                    larkin.sendBare(result, res, next);
                  } else {
                    larkin.sendCompact(result, res, null, next);
                  }
                }
              }
            });
          }
        });
      }
    });
        
  } 
}
