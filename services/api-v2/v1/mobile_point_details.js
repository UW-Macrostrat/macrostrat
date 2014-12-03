var api = require("./api"),
    async = require("async"),
    wellknown = require("wellknown"),
    gp = require("geojson-precision"),
    dbgeo = require("dbgeo"),
    nearestFeature = require("nearest-feature"),
    point = require("turf-point"),
    larkin = require("./larkin");

module.exports = function(req, res, next) {
  if (req.query.lat && req.query.lng) {
    async.parallel({
      gmus: function(callback) {
        larkin.queryPg("earthbase", "SELECT gid, a.rocktype1, a.rocktype2, b.rocktype3, unit_name, b.unit_age, unitdesc FROM gmus.geologic_units a JOIN gmus.units b ON a.unit_link = b.unit_link WHERE ST_Contains(the_geom, ST_GeomFromText($1, 4326))", ["POINT(" + req.query.lng + " " + req.query.lat + ")"], function(error, result) {
          if (error) {
            callback(error);
          } else {
            callback(null, result.rows[0]);
          }
        });
      },

      column: function(callback) {
        async.waterfall([
          function(callbackB) {
            // Find nearest column
            larkin.query("SELECT col_id AS id, col_name, AsWKT(col_areas.col_area) AS col_poly FROM col_areas JOIN cols on col_id=cols.id WHERE ST_CONTAINS(col_areas.col_area,ST_GEOMFROMTEXT('POINT(? ?)')) and status_code='active'", [parseFloat(req.query.lng), parseFloat(req.query.lat)], function(error, result) {
              if (error) {
                callback(error);
              } else {
                /* If a column isn't immediately found, buffer the point by a degree, get all polygons that 
                   intersect that buffer, and then find the closest one */
                if (result.length < 1) {
                  larkin.query("SELECT col_id AS id, col_name, AsWKT(col_areas.col_area) AS col_poly FROM col_areas JOIN cols on col_id=cols.id WHERE ST_Intersects(col_areas.col_area, ST_Buffer(ST_GEOMFROMTEXT('POINT(? ?)'), 1)) and status_code='active'", [parseFloat(req.query.lng), parseFloat(req.query.lat)], function(error, result) {
                    // If no columns are found within 1 degree, return an empty result
                    if (result.length < 1) {
                      callbackB([]);
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

                            callbackB(null, {"id": nearest.properties.id,
                             "col_name": nearest.properties.col_name,
                             "col_poly": wellknown.stringify(nearest.geometry)});
                          }
                        }
                      });
                    }
                  });
                  
                } else {
                  callbackB(null, result[0]);
                }
              }
            });
          },

          function(column, callbackB) {
                
            var sql = "SELECT units.id AS id, units.strat_name, period, max_thick, min_thick, colors.unit_class, count(distinct collection_no) pbdb, lith_short AS lith FROM units \
                JOIN colors ON colors.color = units.color \
                JOIN units_sections ON units_sections.unit_id = units.id \
                JOIN lookup_unit_liths ON lookup_unit_liths.unit_id=units.id \
                JOIN lookup_unit_intervals ON units.id=lookup_unit_intervals.unit_id \
                LEFT JOIN unit_strat_names ON unit_strat_names.unit_id=units.id \
                LEFT JOIN lookup_strat_names ON lookup_strat_names.strat_name_id=unit_strat_names.strat_name_id \
                LEFT JOIN pbdb_matches ON pbdb_matches.unit_id=units.id \
                WHERE units_sections.col_id = ? and pbdb_matches.release_date<NOW() \
                GROUP BY units.id ORDER BY t_age ASC";

            larkin.query(sql, [column.id], function(error, result) {
              if (error) {
                callbackB(error);
              } else {
                callbackB(null, column, result);
              }
            });
          }
        ],
        // after the two queries are executed, send the result
        function(err, column, units) {
          if (err) {
            if (err.length === 0) {
              callback(null, {})
            } else {
              callback(err);
            }
          } else {
            var col = [{
              "id": column.id,
              "col_name": column.col_name,
              "col_poly": (req.query.geo_format === "wkt") ? wellknown.stringify(gp(wellknown(column.col_poly), 3)) : gp(wellknown(column.col_poly), 3),
              "units": units
            }];
            callback(null, col[0]);
          }
        });
      }
    }, function(error, results) {
      if (error) {
        console.log(error);
        larkin.error(req, res, next, "Something went wrong");
      } else {
        larkin.sendData([results], res, "json", next);
      }
    });
  } else if (req.query.col_id && req.query.unit_id) {
    async.parallel({
      gmus: function(callback) {
        larkin.queryPg("earthbase", "SELECT gid, a.rocktype1, a.rocktype2, b.rocktype3, unit_name, b.unit_age, unitdesc FROM gmus.geologic_units a JOIN gmus.units b ON a.unit_link = b.unit_link WHERE gid = $1", [req.query.unit_id], function(error, result) {
          if (error) {
            callback(error);
          } else {
            callback(null, result.rows[0]);
          }
        });
      },

      column: function(callback) {
        async.waterfall([
          function(callbackB) {
            larkin.query("SELECT col_id AS id, col_name, AsWKT(col_areas.col_area) AS col_poly FROM col_areas JOIN cols on col_id=cols.id WHERE cols.id = ?", [req.query.col_id], function(error, result) {
              if (error) {
                callbackB(error);
              } else {
                if (result.length === 0) {
                  callback(null);
                } else {
                  callbackB(null, result[0]);
                }
              }
            });
          },

          function(column, callbackB) {
            larkin.query("SELECT units.id AS id, units.strat_name, period, max_thick, min_thick, color, count(distinct collection_no) AS pbdb, lith_short AS lith FROM units JOIN units_sections ON units_sections.unit_id = units.id JOIN lookup_unit_liths ON lookup_unit_liths.unit_id=units.id JOIN lookup_unit_intervals ON units.id=lookup_unit_intervals.unit_id LEFT JOIN pbdb_matches ON pbdb_matches.unit_id = units.id WHERE units_sections.col_id = ? GROUP BY units.id ORDER BY t_age ASC", [req.query.col_id], function(error, result) {
              if (error) {
                callbackB(error);
              } else {
                callbackB(null, column, result);
              }
            });
          }
        ],
        // after the two queries are executed, send the result
        function(err, column, units) {
          if (err) {
            callback(err);
          } else {
            var col = [{
              "id": column.id,
              "col_name": column.col_name,
              "col_poly": (req.query.geo_format === "wkt") ? wellknown.stringify(gp(wellknown(column.col_poly), 3)) : gp(wellknown(column.col_poly), 3),
              "units": units
            }];
            callback(null, col[0]);
          }
        });
      }
    }, function(error, results) {
      if (error) {
        larkin.error(req, res, next, "Something went wrong");
      } else {
        larkin.sendData([results], res, "json", next);
      }
    });
  } else {
    larkin.info(req, res, next);
  }
}
