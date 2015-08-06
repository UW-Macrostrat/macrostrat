var api = require("./api"),
    async = require("async"),
    multiline = require("multiline"),
    larkin = require("./larkin");

module.exports = function(req, res, next) {
  if (Object.keys(req.query).length < 1) {
    larkin.info(req, res, next);
  } else if ((!("scale" in req.query) || ["small", "medium", "large"].indexOf(req.query.scale) < 0) && !("sample" in req.query)) {
    larkin.error(req, res, next, "A valid scale parameter is required (small, medium, or large)");
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
    async.parallel([

      // Lat/lng
      function(callback) {
        if (req.query.lat && req.query.lng) {
          where.push("ST_Contains(m.geom, ST_GeomFromText($" + (where.length + 1) + ", 4326))");
          params.push("POINT(" + req.query.lng + " " + req.query.lat + ")");
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
          require("./defs/strat_names")(req, null, null, function(error, result) {
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
      }

    ], function() {
      if (where.length < 1 && !("sample" in req.query)) {
        return larkin.error(req, res, next, "Invalid params");
      }

      if (where.length > 0) {
        where = " WHERE " + where.join(" AND ");
      } else {
        where = "";
      }

      var sql = multiline(function() {/*
        SELECT
          m.map_id,
          m.source_id,
          COALESCE(m.name, '') AS name,
          COALESCE(m.strat_name, '') AS strat_name,
          COALESCE(m.lith, '') AS lith,
          COALESCE(m.descrip, '') AS descrip,
          COALESCE(m.comments, '') AS comments,
          mm.unit_ids AS macro_units,
          mm.strat_name_ids AS strat_names,
          m.t_interval AS t_int_id,
          ti.age_top::float AS t_int_age,
          ti.interval_name AS t_int_name,
          m.b_interval AS b_int_id,
          tb.age_bottom::float AS b_int_age,
          tb.interval_name AS b_int_name,
          mm.color
      */});

      sql += " FROM maps." + req.query.scale + " m \
              LEFT JOIN macrostrat.intervals ti ON m.t_interval = ti.id \
              LEFT JOIN macrostrat.intervals tb ON m.b_interval = tb.id \
              LEFT JOIN " + req.query.scale + "_map mm ON mm.map_id = m.map_id"
          + where + limit;


      larkin.queryPg("burwell", sql, params, function(error, result) {
        if (error) {
          larkin.error(req, res, next, error);
        } else {
          larkin.sendCompact(result.rows, res, (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json", next);
        }
      });
    });
  }
}
