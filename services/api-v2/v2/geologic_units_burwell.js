var api = require("./api"),
    async = require("async"),
    dbgeo = require("dbgeo"),
    gp = require("geojson-precision"),
    larkin = require("./larkin");

function buildSQL(req, scale, where, limit) {
  var sql = `
  (SELECT
    m.map_id,
    m.source_id,
    COALESCE(m.name, '') AS name,
    COALESCE(m.strat_name, '') AS strat_name,
    COALESCE(m.lith, '') AS lith,
    COALESCE(m.descrip, '') AS descrip,
    COALESCE(m.comments, '') AS comments,
    COALESCE(mm.unit_ids, '{}') AS macro_units,
    COALESCE(mm.strat_name_ids, '{}') AS strat_names,
    COALESCE(mm.lith_ids, '{}') AS liths,
    m.t_interval AS t_int_id,
    ti.age_top::float AS t_int_age,
    ti.interval_name AS t_int_name,
    m.b_interval AS b_int_id,
    tb.age_bottom::float AS b_int_age,
    tb.interval_name AS b_int_name,
    mm.color,
    mm.best_age_top::float AS t_age,
    mm.best_age_bottom::float AS b_age,
    (SELECT COALESCE(interval_name, '')
     FROM macrostrat.intervals
     JOIN macrostrat.timescales_intervals ON intervals.id = timescales_intervals.interval_id
     JOIN macrostrat.timescales ON timescales_intervals.timescale_id = timescales.id
     WHERE age_top <= mm.best_age_top::float AND age_bottom >= mm.best_age_bottom::float
     AND timescales.id IN (11,14)
     ORDER BY age_bottom - age_top
     LIMIT 1
    ) AS best_int_name
  `
  if (req.query.map) {
    sql = "(SELECT mm.color, m.source_id"
  }

  if (req.query.format && api.acceptedFormats.geo[req.query.format]) {
    sql += ", ST_AsGeoJSON(m.geom) AS geometry"
  }

  sql += " FROM maps." + scale + " m \
          LEFT JOIN macrostrat.intervals ti ON m.t_interval = ti.id \
          LEFT JOIN macrostrat.intervals tb ON m.b_interval = tb.id \
          LEFT JOIN lookup_" + scale + " mm ON mm.map_id = m.map_id"
      + where + limit + ")";

  return sql;
}

module.exports = function(req, res, next, cb) {
  if (Object.keys(req.query).length < 1) {
    larkin.info(req, res, next);
  } else {
    var where = [],
        params = [],
        limit;

    if ("sample" in req.query) {
      limit = " LIMIT 5";
      req.query.scale = "medium";
    } else {
      limit = ""
    }

    // Process the parameters
    async.parallel([

      // Lat/lng
      function(callback) {
        if (req.query.lat && req.query.lng) {
          req.query.lng = larkin.normalizeLng(req.query.lng);
          if (req.query.buffer && req.query.buffer <= 50) {
            where.push("ST_Intersects(m.geom, ST_Buffer(ST_GeographyFromText($" + (where.length + 1) + "), $" + (where.length + 2) + ")::geometry)");
            params.push("POINT(" + req.query.lng + " " + req.query.lat + ")", req.query.buffer * 1000);
          } else {
            where.push("ST_Intersects(m.geom, ST_GeomFromText($" + (where.length + 1) + ", 4326))");
            params.push("POINT(" + req.query.lng + " " + req.query.lat + ")");
          }

        }
        callback(null);
      },

      // map_id
      function(callback) {
        if (req.query.map_id && req.query.map_id != "undefined") {
          where.push("m.map_id = ANY($" + (where.length + 1) + ")");
          params.push(larkin.parseMultipleIds(req.query.map_id));
        }

        callback(null);
      },

      // strat_name_id
      function(callback) {
        // Need to go down the hierarchy!
        if (req.query.strat_name_id) {
          req.query.rule = "down";
          require("./definitions/strat_names")(req, null, null, function(error, result) {
            if (error || !result) {
              return callback(null)
            }
            var strat_name_ids = result.map(function(d) { return d.strat_name_id });

            where.push("mm.strat_name_ids && $" + (where.length + 1) + "::int[]");
            params.push(strat_name_ids);
            callback(null);
          });
        } else {
          callback(null);
        }

      },

      // unit_id
      function(callback) {
        if (req.query.unit_id) {
          var unit_ids = larkin.parseMultipleIds(req.query.unit_id);

          where.push("mm.unit_ids && $" + (where.length + 1) + "::int[]");
          params.push(unit_ids);
        }

        callback(null);
      },

      // lith_id
      function(callback) {
        if (req.query.lith_id) {
          var lith_ids = larkin.parseMultipleIds(req.query.lith_id);

          where.push("mm.lith_ids && $" + (where.length + 1) + "::int[]");
          params.push(lith_ids);
        }

        callback(null);
      }

    ], function() {
      // If no valid parameters passed, return an Error
      if (where.length < 1 && !("sample" in req.query)) {
        if (cb) return cb("No valid parameters passed");
        return larkin.error(req, res, next, "No valid parameters passed");
      }

      if (where.length > 0) {
        where = " WHERE " + where.join(" AND ");
      } else {
        where = "";
      }

      if (req.query.scale) {
        var requestedScales = larkin.parseMultipleStrings(req.query.scale);
            scales = requestedScales.filter(function(d) {
              if (["tiny", "small", "medium", "large"].indexOf(d) > -1) {
                return d;
              }
            });

        if (scales.length < 1) {
          return larkin.error(req, res, next, "Invalid scale parameter passed.");
        }
      } else {
        scales = ["tiny", "small", "medium", "large"];
      }


      var scaleSQL = scales.map(function(d) {
        return buildSQL(req, d, where, limit);
      }).join(" UNION ");

      var toRun = "SELECT * FROM ( " + scaleSQL + ") doit";

      larkin.queryPg("burwell", toRun, params, function(error, result) {
        if (error) {
          if (cb) return cb(error);
          larkin.error(req, res, next, error);
        } else {
          if (req.query.format && api.acceptedFormats.geo[req.query.format]) {
            dbgeo.parse(result.rows, {
              "geometryType": "geojson",
              "geometryColumn": "geometry",
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
