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
          params = [],
          orderBy = "";

      if (req.query.lat && req.query.lng) {
        if (req.query.adjacents === "true") {
          where.push("ST_Intersects(geom, ST_Buffer(ST_GeomFromText($" + (where.length) + 1 + ", 4326), 0.5))")
          params.push("POINT(" + req.query.lng + " " + req.query.lat + ")");
          orderBy += " )a ORDER BY ST_Distance(geom, ST_GeomFromText($" + where.length + ", 4326))";
        } else {
          where.push(" ST_Contains(geom, ST_GeomFromText($" + (where.length + 1) + ", 4326))");
          params.push("POINT(" + req.query.lng + " " + req.query.lat + ")");
        }
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
        where.push("macro_b_age <= (SELECT age_bottom FROM macrostrat.intervals WHERE interval_name = $" + (where.length + 1) + ") AND macro_t_age >= (SELECT age_top FROM macrostrat.intervals WHERE interval_name = $" + (where.length + 2) + ")");
        params.push(req.query.interval_name, req.query.interval_name);
      }

      if (req.query.unit_link) {
        where.push(" lu.unit_link = $" + (where.length + 1));
        params.push(req.query.unit_link);
      }

      if (where.length === 0) {
        return larkin.error(req, res, next, "Invalid params");
      }

      larkin.queryPg("geomacro", ((orderBy.length > 0) ? "SELECT gid, interval_color, lith1, lith2, lith3, lith4, lith5, macro_units, min_age, age_top, max_age, age_bottom, rt1, rt2, rt3, unit_age, unit_com, unit_link, unit_name, unitdesc, strat_unit" + ((geo) ? ", geometry" : "") + " FROM (" : "" ) + "SELECT DISTINCT ON (gid) gid, macro_color AS interval_color, lith1, lith2, lith3, lith4, lith5, COALESCE(gm.best_units, '{}') AS macro_units, COALESCE(gm.best_names, '{}') AS strat_names, lu.min_interval_name AS min_age, lu.age_top, lu.max_interval_name as max_age, lu.age_bottom, u_rocktype1 AS rt1, u_rocktype2 AS rt2, u_rocktype3 AS rt3, lu.containing_interval_name AS unit_age,  unit_com, lu.unit_link, unit_name, unitdesc, strat_unit" + ((orderBy.length > 0) ? ", geom" : "") + ((geo) ? ", ST_AsGeoJSON(geom) AS geometry" : "") + " FROM gmus.lookup_units lu JOIN gmus.ages a ON lu.unit_link = a.unit_link LEFT JOIN gmus.liths l ON lu.unit_link = l.unit_link LEFT JOIN gmus.best_geounits_macrounits gm ON lu.gid = gm.geologic_unit_gid WHERE " + where.join(", ") + orderBy, params, function(error, result) {
        if (error) {
          larkin.error(req, res, next, error);
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

      if (req.query.gid && req.query.gid != "undefined") {
        where.push(" gid = " + (where.length + 1));
        params.push(req.query.gid);
      }

      if (req.query.lat && req.query.lng) {
        where.push(" ST_Contains(geom, ST_GeomFromText($" + (where.length + 1)+ ", 4326))");
        params.push("POINT(" + req.query.lng + " " + req.query.lat + ")");
      }

      if (req.query.interval_name) {
        where.push(" max_age <= (SELECT age_bottom FROM macrostrat.intervals WHERE interval_name = $" + (where.length + 1) + ") AND min_age >= (SELECT age_top FROM macrostrat.intervals WHERE interval_name = $" + (where.length + 2) + ")");
        params.push(req.query.interval_name, req.query.interval_name);
      }

      larkin.queryPg("geomacro", "SELECT unit_abbre, rocktype, lithology, min_interval AS min_age, min_age AS age_top, max_interval AS max_age, max_age AS age_bottom, containing_interval AS interval_name" + ((geo) ? ", ST_AsGeoJSON(geom) AS geometry" : "") + " FROM gmna.lookup_units WHERE " + where.join(", "), params, function(error, result) {
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
