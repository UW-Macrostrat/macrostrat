var api = require("./api"),
    async = require("async"),
    dbgeo = require("dbgeo"),
    nearestFeature = require("nearest-feature"),
    point = require("turf-point"),
    larkin = require("./larkin");

module.exports = function(req, res, next) {
  if (req.query.lat && req.query.lng) {
    async.parallel({
      gmus: function(callback) {
        larkin.queryPg("earthbase", "SELECT gid, state, a.rocktype1, a.rocktype2, b.rocktype3, unit_name, b.unit_age, unitdesc, strat_unit, unit_com FROM gmus.geologic_units a JOIN gmus.units b ON a.unit_link = b.unit_link WHERE ST_Contains(the_geom, ST_GeomFromText($1, 4326))", ["POINT(" + req.query.lng + " " + req.query.lat + ")"], function(error, result) {
          if (error) {
            callback(error);
          } else {
            callback(null, result.rows[0]);
          }
        });
      },

      gmna: function(callback) {
        larkin.queryPg("earthbase", "SELECT objectid AS id, unit_abbre, rocktype, lithology, interval_name, map_unit_n FROM gmna.gmna_for_maps WHERE ST_Contains(the_geom, ST_GeomFromText($1, 4326))", ["POINT(" + req.query.lng + " " + req.query.lat + ")"], function(error, result) {
          if (error) {
            callback(error);
          } else {
            callback(null, result.rows[0]);
          }
        });
      },

      // Query Macrostrat for polygon
      column: function(callback) {
        larkin.query("SELECT col_id FROM col_areas JOIN cols on col_id = cols.id WHERE ST_CONTAINS(col_areas.col_area, ST_GEOMFROMTEXT('POINT(? ?)')) and status_code='active'", [parseFloat(req.query.lng), parseFloat(req.query.lat)], function(error, result) {
            if (error) {
              callback(error);
            } else {
              if (result.length === 1) {
                callback(null, result[0]);
              } else {
                larkin.query("SELECT col_id AS id, AsWKT(col_areas.col_area) AS col_poly FROM col_areas JOIN cols on col_id=cols.id WHERE ST_Intersects(col_areas.col_area, ST_Buffer(ST_GEOMFROMTEXT('POINT(? ?)'), 1)) and status_code='active'", [parseFloat(req.query.lng), parseFloat(req.query.lat)], function(error, result) {
                  // If no columns are found within 1 degree, return an empty result
                  if (result.length < 1) {
                    callback(null, {});
                  } else {
                    dbgeo.parse({
                      "data": result,
                      "geometryColumn": "col_poly",
                      "geometryType": "wkt",
                      "callback": function(error, geojson) {
                        if (error) {
                          callback(error);
                        } else {
                          var nearest = nearestFeature(point(parseFloat(req.query.lng), parseFloat(req.query.lat)), geojson);

                          callback(null, { "col_id": nearest.properties.id });
                        }
                      }
                    });
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
