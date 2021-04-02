var api = require("./api"),
    async = require("async"),
    larkin = require("./larkin");

module.exports = function(req, res, next, cb) {
  if (Object.keys(req.query).length < 1) {
    larkin.info(req, res, next);
  } else {
    var where = [],
        where_lith = [],
        params = [],
        params_lith = [],
        limit;

    if ("sample" in req.query) {
      limit = " LIMIT 5";
    } else {
      limit = ""
    }

    // Process the parameters
    async.parallel([

      // Lat/lng
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

            where.push("m.strat_name_ids && $" + (where.length + 1) + "::int[]");
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

          where.push("m.unit_ids && $" + (where.length + 1) + "::int[]");
          params.push(unit_ids);
        }

        callback(null);
      },

      // scale
      function(callback) {
        if (req.query.scale) {
          where.push('scale = ANY($' + (where.length + 1) + ')')
          params.push(larkin.parseMultipleStrings(req.query.scale))
        }

        callback(null);
      },

      // comments
      function(callback) {
        if (req.query.comments) {
          where.push('comments ILIKE $' + (where.length + 1))
          params.push('%' + req.query.comments + '%')
        }

        callback(null);
      },

      // descrip
      function(callback) {
        if (req.query.description) {
          where.push('descrip ILIKE $' + (where.length + 1))
          params.push('%' + req.query.description + '%')
        }

        callback(null);
      },

      // source_id
      function(callback) {
        if (req.query.source_id) {
          where.push('source_id = ANY($' + (where.length + 1) + ')')
          params.push(larkin.parseMultipleIds(req.query.source_id))
        }

        callback(null);
      },

      // lith_id
      function(callback) {
        if (req.query.lith_id) {
          var lith_ids = larkin.parseMultipleIds(req.query.lith_id);

          where_lith.push("m.lith_ids && $" + (where_lith.length + 1 + where.length) + "::int[]");
          params_lith.push(lith_ids);
        }

        callback(null);
      },

      // lith_type
      function(callback) {
        if (req.query.lith_type) {
          var lith_type = larkin.parseMultipleStrings(req.query.lith_type);

          where_lith.push("m.lith_types && $" + (where_lith.length + 1 + where.length) + "");
          params_lith.push(lith_type);
        }

        callback(null);
      },

      // lith_classes
      function(callback) {
        if (req.query.lith_class) {
          var lith_class = larkin.parseMultipleStrings(req.query.lith_class);

          where_lith.push("m.lith_classes && $" + (where_lith.length + 1 + where.length) + "");
          params_lith.push(lith_class);
        }

        callback(null);
      }

    ], function() {
      // If no valid parameters passed, return an Error
      if (where.length < 1 && where_lith.length < 1 && !("sample" in req.query)) {
        if (cb) return cb("No valid parameters passed");
        return larkin.error(req, res, next, "No valid parameters passed");
      }

      var where_start = "";
      if (where.length > 0) {
        where_start = " WHERE ";
        where = " " + where.join(" AND ");
      } else {
        where = "";
      }

      if (where_lith.length > 0) {
        where_start = " WHERE ";
        where_lith = "(" + where_lith.join(" OR ") + ")";
      } else {
        where_lith = "";
      }

       var where_combined = '';
       if (where_lith.length > 0 && where.length > 0) {
         where = where + " AND "
         where_combined = where.concat(where_lith);
         where = "";
         where_lith = "";
       }

      var params_combined = params.concat(params_lith);

      var sql = "SELECT legend_id, source_id, scale, m.name as map_unit_name, strat_name,age,to_json(lith) AS lith,to_json(descrip) AS descrip, to_json(comments) AS comments,best_age_top::float t_age,best_age_bottom::float b_age,b_interval,t_interval,strat_name_ids strat_name_id,lith_classes,lith_types,lith_ids lith_id ,color,m.area::float,tiny_area::float,small_area::float,medium_area::float,large_area::float";

      sql += " FROM maps.legend m JOIN maps.sources USING (source_id)"
        + where_start + where + where_combined + where_lith + limit;

//      var scaleSQL = buildSQL(req, where, limit);

//      var toRun = "SELECT * FROM ( " + scaleSQL + ") doit";
// console.log(sql,params_combined);

      larkin.queryPg("burwell", sql, params_combined, function(error, result) {
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
