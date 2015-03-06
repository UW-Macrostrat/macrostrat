var api = require("./api"),
    async = require("async"),
    wellknown = require("wellknown"),
    gp = require("geojson-precision"),
    dbgeo = require("dbgeo"),
    larkin = require("./larkin");

module.exports = function(req, res, next) {
  if (Object.keys(req.query).length < 1) {
    larkin.info(req, res, next);
  } else {
    var geo = (req.query.format && api.acceptedFormats.geo[req.query.format]) ? true : false,
        types = (req.query.type) ? req.query.type.split(",") : ["gmna", "gmus"];

    if (["gmna", "gmus"].indexOf(req.query.type) < 0) {
      return larkin.error(req, res, next, "Please enter a valid map type to query (gmna or gmus)");
    }

    if (req.query.type === "gmus") {
      var where = [],
          params = [];

      if (req.query.lat && req.query.lng) {
        where.push(" ST_Contains(the_geom, ST_GeomFromText($" + (where.length + 1) + ", 4326))");
        params.push("POINT(" + req.query.lng + " " + req.query.lat + ")");
      }

      if (req.query.gid && req.query.gid != "undefined") {
        where.push("gid = $" + (where.length + 1));
        params.push(req.query.gid);
      }

      if (req.query.unit_name) {
        where.push("text_search @@ plainto_tsquery('macro', $" + (where.length + 1) + ")")
        params.push(req.query.unit_name);
      }

      if (req.query.interval_name) {
        where.push("macro_b_age <= (SELECT age_bottom FROM macrostrat.intervals WHERE interval_name = $" + (where.length + 1) + ") AND macro_t_age <= (SELECT age_top FROM macrostrat.intervals WHERE interval_name = $" + (where.length + 2) + ")");
        params.push(req.query.interval_name, req.query.interval_name);
      }

      if (where.length === 0) {
        return larkin.error(req, res, next, "Invalid params");
      }

      larkin.queryPg("geomacro", "SELECT DISTINCT ON (gid) gid, macro_color AS interval_color, lith1, lith2, lith3, lith4, lith5, gm.best_units AS macro_units, i1.interval_name AS min_age, i2.interval_name as max_age, u_rocktype1 AS rt1, u_rocktype2 AS rt2, u_rocktype3 AS rt3, lu.interval_name AS unit_age, unit_com, lu.unit_link, unit_name, unitdesc, strat_unit" + ((geo) ? ", ST_AsGeoJSON(geom) AS geometry" : "") + " FROM gmus.lookup_units lu JOIN gmus.ages a ON lu.unit_link = a.unit_link JOIN macrostrat.intervals i1 ON a.macro_min_interval_id = i1.id JOIN macrostrat.intervals i2 ON a.macro_max_interval_id = i2.id LEFT JOIN gmus.liths l ON lu.unit_link = l.unit_link LEFT JOIN gmus.best_geounits_macrounits gm ON lu.gid = gm.geologic_unit_gid WHERE " + where.join(", "), params, function(error, result) {
        if (error) {
          callback(error);
        } else {
          if (geo) {
            dbgeo.parse({
              "data": result.rows,
              "outputFormat": larkin.getOutputFormat(req.query.format),
              "callback": function(error, result) {
                if (error) {
                  larkin.error(req, res, next, error);
                } else {
                  if (larkin.getOutputFormat(req.query.format) === "geojson") {
                    result = gp(result, 5);
                  }
                  if (api.acceptedFormats.bare[req.query.format]) {
                    larkin.sendBare(result, res, next);
                  } else {
                    larkin.sendCompact(result, res, null, next);
                  }
                }
              }
            });
          } else {
            larkin.sendCompact(result.rows, res, null, next);
          }
        }
      });

/* IF GMNA */
    } else if (req.query.type === "gmna") {
      var where = [],
          params = [];

      if (req.query.lat && req.query.lng) {
        where.push(" ST_Contains(geom, ST_GeomFromText($" + (where.length + 1)+ ", 4326))");
        params.push("POINT(" + req.query.lng + " " + req.query.lat + ")");
      }

      if (req.query.interval_name) {
        where.push(" min_interval ILIKE $" + (where.length + 1) + " OR max_interval ILIKE $" + (where.length + 2));
        params.push(req.query.interval_name, req.query.interval_name);
      }

      larkin.queryPg("geomacro", "SELECT unit_abbre, rocktype, lithology, min_interval AS min_age, max_interval AS max_age, containing_interval AS interval_name" + ((geo) ? ", ST_AsGeoJSON(geom) AS geometry" : "") + " FROM gmna.lookup_units WHERE " + where.join(", "), params, function(error, result) {
        if (error) {
          callback(error);
        } else {
          if (geo) {
            dbgeo.parse({
              "data": result.rows,
              "outputFormat": larkin.getOutputFormat(req.query.format),
              "callback": function(error, result) {
                if (error) {
                  larkin.error(req, res, next, error);
                } else {
                  if (larkin.getOutputFormat(req.query.format) === "geojson") {
                    result = gp(result, 5);
                  }
                  if (api.acceptedFormats.bare[req.query.format]) {
                    larkin.sendBare(result, res, next);
                  } else {
                    larkin.sendCompact(result, res, null, next);
                  }
                }
              }
            });
          } else {
            larkin.sendCompact(result.rows, res, null, next);
          }
        }
      });
    }
  }
}
