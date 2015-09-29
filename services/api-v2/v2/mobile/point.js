var api = require("../api"),
    async = require("async"),
    larkin = require("../larkin");

module.exports = function(req, res, next) {
  if (req.query.lat && req.query.lng) {
    async.parallel({
      gmus: function(callback) {
        larkin.queryPg("geomacro", "SELECT gid, state, (CASE WHEN (rocktype1 IS NULL) THEN '' ELSE rocktype1 END) AS rocktype1, (CASE WHEN (rocktype2 IS NULL) THEN '' ELSE rocktype2 END) AS rocktype2, (CASE WHEN (u_rocktype3 IS NULL) THEN '' ELSE u_rocktype3 END) AS rocktype3, unit_name, unit_age, unitdesc, strat_unit, unit_com FROM gmus.lookup_units WHERE ST_Contains(geom, ST_GeomFromText($1, 4326))", ["POINT(" + req.query.lng + " " + req.query.lat + ")"], function(error, result) {
          if (error) {
            callback(error);
          } else {
            callback(null, result.rows[0]);
          }
        });
      },

      gmna: function(callback) {
        larkin.queryPg("geomacro", "SELECT gid AS id, unit_abbre, rocktype, lithology, containing_interval AS interval_name, map_unit_n FROM gmna.lookup_units WHERE ST_Contains(geom, ST_GeomFromText($1, 4326))", ["POINT(" + req.query.lng + " " + req.query.lat + ")"], function(error, result) {
          if (error) {
            callback(error);
          } else {
            callback(null, result.rows[0]);
          }
        });
      },

      // Query Macrostrat for polygon
      column: function(callback) {
        larkin.queryPg("geomacro", "SELECT id AS col_id FROM macrostrat.cols WHERE ST_Contains(poly_geom, ST_GeomFromText($1, 4326)) and status_code='active'", ["POINT(" + req.query.lng + " " + req.query.lat + ")"], function(error, result) {
            if (error) {
              callback(error);
            } else {
              if (result.rows.length === 1) {
                callback(null, result.rows[0]);
              } else {
                larkin.queryPg("geomacro", "SELECT id AS col_id FROM macrostrat.cols WHERE ST_Intersects(poly_geom, ST_Buffer(ST_GeomFromText($1, 4326), 1)) and status_code='active' ORDER BY ST_Distance(ST_GeomFromText($1, 4326), poly_geom) LIMIT 1", ["POINT(" + req.query.lng + " " + req.query.lat + ")"], function(error, result) {
                  if (error) {
                    callback(error);

                  // If no columns are found within 1 degree, return an empty result
                  } else if (result.rows.length < 1) {
                    callback(null, {});
                  } else {
                  // Otherwise return the closest one
                    callback(null, { "col_id": result.rows[0].col_id });
                  }
                });
              }
            }
          });
      }
    }, function(error, result) {
      if (error) {
        larkin.error(req, res, next, error);
      } else {
        var response = {
          "uid": (result.gmus && result.gmus.gid) ? result.gmus.gid : (result.gmna && result.gmna.id) ? result.gmna.id : "",
          "rocktype": (result.gmus && result.gmus.rocktype1) ? [result.gmus.rocktype1, result.gmus.rocktype2, result.gmus.rocktype3].filter(function(d) { if (d) return d }) : (result.gmna && (result.gmna.rocktype || result.gmna.lithology)) ? [result.gmna.rocktype, result.gmna.lithology].filter(function(d) { if (d) return d }) : [],
          "age": (result.gmus && result.gmus.unit_age) ? result.gmus.unit_age : (result.gmna && result.gmna.interval_name) ? result.gmna.interval_name : "",
          "name": (result.gmus && result.gmus.unit_name) ? result.gmus.unit_name : (result.gmna && result.gmna.rocktype) ? result.gmna.rocktype + ((result.gmna.lithology) ? ", " + result.gmna.lithology : "") : "",
          "desc": (result.gmus && result.gmus.unitdesc) ? result.gmus.unitdesc : "",
          "comm": (result.gmus && result.gmus.unit_com) ? result.gmus.unit_com : (result.gmna && result.gmna.map_unit_n) ? result.gmna.map_unit_n : "",
          "strat_unit": (result.gmus && result.gmus.strat_unit) ? result.gmus.strat_unit : "",
          "col_id": (result.column && result.column.col_id) ? result.column.col_id : ""
        };
        larkin.sendCompact(response, res, null, next);
      }
    });
      
  } else {
    larkin.info(req, res, next);
  } 
}
