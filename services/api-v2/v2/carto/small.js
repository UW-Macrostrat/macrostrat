var api = require("../api"),
    async = require("async"),
    dbgeo = require("dbgeo"),
    gp = require("geojson-precision"),
    larkin = require("../larkin");

module.exports = function(req, res, next, cb) {
  if (Object.keys(req.query).length < 1) {
    larkin.info(req, res, next);
  } else {
    var where = [],
        params = [];
    var pre = "";

    // Process the parameters
    async.parallel([

      // Lat/lng
      function(callback) {
        if (req.query.lat && req.query.lng) {
          req.query.lng = larkin.normalizeLng(req.query.lng);
          where.push("ST_Intersects(geom, ST_GeomFromText($" + (where.length + 1) + ", 4326))");
          params.push("POINT(" + req.query.lng + " " + req.query.lat + ")");
        }
        callback(null);
      },

      // shape
      function(callback) {
        if (req.query.shape) {
          // Validate
          larkin.queryPg("burwell", "SELECT $1::geometry", [req.query.shape], function(error, done) {
            if (error) return callback(error);

            pre = `
              WITH shape AS (
                SELECT ST_Segmentize($1::geography, 100000)::geometry AS buffer
              )
            `;

            params.push(req.query.shape);

            callback(null);
          });
        } else {
          callback(null);
        }
      }

    ], function(error) {
      if (error) {
        return larkin.error(req, res, next, "Invalid geometry passed");
      }
      // If no valid parameters passed, return an Error
      if (where.length < 1 && !("sample" in req.query) && pre.length < 1) {
        if (cb) return cb("No valid parameters passed");
        return larkin.error(req, res, next, "No valid parameters passed");
      }

      if (where.length > 0) {
        where = " WHERE " + where.join(" AND ");
      } else {
        where = "";
      }

      if ("sample" in req.query) {
        var limit = " LIMIT 5";
      } else {
        limit = ""
      }

      var sql = pre + " SELECT map_id, scale, source_id, name, strat_name, age, lith, descrip, comments, best_age_top, best_age_bottom, t_int, b_int, color";
      var join = "";

      if (req.query.format && api.acceptedFormats.geo[req.query.format]) {
        if (req.query.shape) {
          sql += `,
            CASE
              WHEN ST_Within(geom, shape.buffer)
                THEN ST_AsGeoJSON(geom)
              ELSE ST_AsGeoJSON(ST_Multi(ST_Intersection(geom, shape.buffer)))
            END AS geometry
          `;
          join = `
            JOIN shape
            ON ST_Intersects(geom, shape.buffer)
          `;

        } else {
          sql += ", ST_AsGeoJSON(geom) geometry";
        }
      }

      sql += " FROM carto.small " + join + where + limit;

      larkin.queryPg("burwell", sql, params, function(error, result) {
        if (error) {
          if (cb) return cb(error);
          larkin.error(req, res, next, error);
        } else {
          if (req.query.format && api.acceptedFormats.geo[req.query.format]) {
            dbgeo.parse({
              "data": result.rows,
              "outputFormat": larkin.getOutputFormat(req.query.format)
            }, function(error, result) {
              if (error) {
                if (cb) return cb(error);
                larkin.error(req, res, next, error);
              } else {
                if (larkin.getOutputFormat(req.query.format) === "geojson") {
                  result = gp(result, 5);
                }
                if (cb) return cb(null, result);
                larkin.sendData(req, res, next, {
                  format: (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json",
                  bare: (api.acceptedFormats.bare[req.query.format]) ? true : false,
                  refs: 'source_id'
                }, {
                  data: result
                });
              }
            });
          } else {
            if (cb) return cb(null, result.rows);
            larkin.sendData(req, res, next, {
              format: (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json",
              bare: (api.acceptedFormats.bare[req.query.format]) ? true : false,
              refs: 'source_id'
            }, {
              data: result.rows
            });
          }
        }
      });
    });
  }
}
