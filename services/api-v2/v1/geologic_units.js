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
        types = (req.query.type) ? req.query.type.split(",") : ["gmna", "gmus", "column"];

    if (["gmna", "gmus"].indexOf(req.query.type) < 0) {
      return larkin.error(req, res, next, "Please enter a valid map type to query (gmna or gmus)");
    }

    if (req.query.type === "gmus") {
      var where = "",
          params = [];

      if (req.query.lat && req.query.lng) {
        var placeholder = "$" + (params.length + 1);
        where += " WHERE ST_Contains(the_geom, ST_GeomFromText(" + placeholder + ", 4326))";
        params.push("POINT(" + req.query.lng + " " + req.query.lat + ")");
      }
      /*if (req.query.rocktype) {
        if (where.length < 1) {
          where += " WHERE "
        } else {
          where += " AND "
        }
        var placeholder = "$" + (params.length + 1);
        where += "(a.rocktype1 ILIKE " + placeholder + " OR a.rocktype2 ILIKE " + placeholder + " OR b.rocktype3 ILIKE " + placeholder + ")";
        params.push("%" + req.query.rocktype + "%");
      }*/
      if (req.query.unit_name) {
        if (where.length < 1) {
          where += " WHERE "
        } else {
          where += " AND "
        }
        var placeholder = "$" + (params.length + 1);
        where += " unit_name ILIKE " + placeholder;
        params.push("%" + req.query.unit_name + "%");
      }

      if (req.query.interval_name) {
        if (where.length < 1) {
          where += " WHERE "
        } else {
          where += " AND "
        }
        var placeholder = "$" + (params.length + 1);
        where += " c.cmin_age = " + placeholder;
        params.push(req.query.interval_name);
      }

      if (where === "" || params.length === 0) {
        return larkin.error(req, res, next, "Invalid params");
      }
      larkin.queryPg("earthbase", "SELECT a.unit_link, u_rocktype1 AS rt1, u_rocktype2 AS rt2, u_rocktype3 AS rt3, unit_name, unit_age, interval_color, c.cmin_age AS min_age, c.cmax_age AS max_age, lith1, lith2, lith3, lith4, lith5, unitdesc, a.gid" + ((geo) ? ", ST_AsGeoJSON(the_geom) AS geometry" : "") + " FROM gmus.geologic_units_with_intervals a LEFT JOIN gmus.lith b ON a.unit_link = b.unit_link LEFT JOIN gmus.age c ON a.unit_link = c.unit_link" + where, params, function(error, result) {
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
      var where = "",
          params = [];

      if (req.query.lat && req.query.lng) {
        var placeholder = "$" + (params.length + 1);
        where += " WHERE ST_Contains(the_geom, ST_GeomFromText(" + placeholder + ", 4326))";
        params.push("POINT(" + req.query.lng + " " + req.query.lat + ")");
      }

      if (req.query.interval_name) {
        if (where.length < 1) {
          where += " WHERE "
        } else {
          where += " AND "
        }
        var placeholder = "$" + (params.length + 1);
        where += " b.interval_name ILIKE " + placeholder + " OR b.interval_name ILIKE " + placeholder;
        params.push(req.query.interval_name);
      }

      larkin.queryPg("earthbase", "SELECT unit_abbre, rocktype, lithology, min_age, max_age, b.interval_name" + ((geo) ? ", ST_AsGeoJSON(the_geom) AS geometry" : "") + " FROM gmna.geologic_units a LEFT JOIN gmna.intervals_old b ON a.eb_interval_id = b.interval_id" + where, params, function(error, result) {
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
