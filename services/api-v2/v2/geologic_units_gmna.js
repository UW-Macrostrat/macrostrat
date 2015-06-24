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
    var geo = (req.query.format && api.acceptedFormats.geo[req.query.format]) ? true : false;

    var where = [],
        params = [],
        limit = ("sample" in req.query) ? " LIMIT 5" : "",
        geomField = ((geo) ? ", ST_AsGeoJSON(geom) AS geometry" : ""),
        from = "";

    if (req.query.gid && req.query.gid != "undefined") {
      where.push(" gid = $" + (where.length + 1));
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

    if (req.query.shape) {
      var buffer = (req.query.buffer && !isNaN(parseInt(req.query.buffer))) ? parseInt(req.query.buffer)*1000 : 1;

      from += ", (SELECT ST_Buffer(ST_SnapToGrid($" + (where.length + 1) + "::geometry, 0.1)::geography, $" + (where.length + 2) + ") AS buffer) shape";
      where.push("ST_Intersects(geom, buffer) is true");
      params.push(req.query.shape, buffer);

      geomField = ((geo) ? ", ST_AsGeoJSON(ST_Intersection(geom, buffer)) AS geometry" : "");
    }

    if (where.length < 1 && !("sample" in req.query)) {
      return larkin.error(req, res, next, "Invalid params");
    }

    if (where.length > 0) {
      where = " WHERE " + where.join(", ");
    }

    larkin.queryPg("geomacro", "SELECT gid, unit_abbre, COALESCE(rocktype, '') AS rocktype, COALESCE(lithology, '') AS lith, lith_type, lith_class, min_interval AS t_interval, min_age::float AS t_age, max_interval AS b_interval, max_age::float AS b_age, containing_interval, interval_color AS color" + geomField + " FROM gmna.lookup_units" + from + where + limit, params, function(error, result) {
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
          larkin.sendCompact(result.rows, res, (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json", next);
        }
      }
    });
  }
}
