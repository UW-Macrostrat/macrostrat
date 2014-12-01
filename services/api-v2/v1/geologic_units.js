var api = require("./api"),
    async = require("async"),
    wellknown = require("wellknown"),
    gp = require("geojson-precision"),
    larkin = require("./larkin");

module.exports = function(req, res, next) {
  if (Object.keys(req.query).length < 1) {
    larkin.info(req, res, next);
  } else {
    var geo = (req.query.geo && req.query.geo === "true") ? true : false,
        types = (req.query.type) ? req.query.type.split(",") : ["gmna", "gmus", "column"];

    async.parallel({
      gmus: function(callback) {
        if (types.indexOf("gmus") > -1) {
          larkin.queryPg("earthbase", "SELECT gid, state, a.rocktype1, a.rocktype2, b.rocktype3, unit_name, b.unit_age, unitdesc, strat_unit, unit_com" + ((geo) ? ", ST_AsGeoJSON(a.the_geom) AS geometry" : "") + " FROM gmus.geologic_units a JOIN gmus.units b ON a.unit_link = b.unit_link WHERE ST_Contains(the_geom, ST_GeomFromText($1, 4326))", ["POINT(" + req.query.lng + " " + req.query.lat + ")"], function(error, result) {
            if (error) {
              callback(error);
            } else {
              if (geo) {
                result.rows[0].geometry = gp(JSON.parse(result.rows[0].geometry), 6);
              }
              callback(null, result.rows[0]);
            }
          });
        } else {
          callback(null);
        } 
      },

      gmna: function(callback) {
        if (types.indexOf("gmna") > -1) {
          larkin.queryPg("earthbase", "SELECT objectid, unit_abbre, rocktype, lithology, min_age, max_age, min_max_re, unit_uncer, age_uncert" + ((geo) ? ", ST_AsGeoJSON(the_geom) AS geometry" : "") + " FROM gmna.geologic_units WHERE ST_Contains(the_geom, ST_GeomFromText($1, 4326))", ["POINT(" + req.query.lng + " " + req.query.lat + ")"], function(error, result) {
            if (error) {
              callback(error);
            } else {
              if (geo) {
                result.rows[0].geometry = gp(JSON.parse(result.rows[0].geometry), 6);
              }
              callback(null, result.rows[0]);
            }
          });
        } else {
          callback(null);
        }
      },

      column: function(callback) {
        if (types.indexOf("column") > -1) {
          async.waterfall([
            function(callbackB) {
              // Find nearest column
              larkin.query("SELECT col_id " + ((geo) ? ", AsWKT(col_areas.col_area) AS wkt" : "") + " FROM col_areas JOIN cols on col_id=cols.id WHERE ST_CONTAINS(col_areas.col_area,ST_GEOMFROMTEXT('POINT(? ?)')) and status_code='active'", [parseFloat(req.query.lng), parseFloat(req.query.lat)], function(error, result) {
                if (error) {
                  callback(error);
                } else {
                  if (result.length < 1) {
                    callbackB("No columns found");
                  } else if (result.length > 1) {
                    callbackB("More than 1 column found");
                  } else {
                    callbackB(null, result[0]);
                  }
                }
              });
            },

            function(column, callbackB) {
              larkin.query("SELECT id, col_name FROM cols WHERE id = ?", [column.col_id], function(error, result) {
                if (error) {
                  callbackB(error);
                } else {
                  if (result.length === 0) {
                    callback(null);
                  } else {
                    callbackB(null, column, result[0]);
                  }
                }
              });
            },

            function(column, column_info, callbackB) {
              var shortSQL = "units.id AS id,units.strat_name, mbr_name Mbr, fm_name Fm, gp_name Gp, sgp_name SGp, era, period, max_thick, min_thick, color, lith_type, count(distinct collection_no) pbdb";
                  
              var longSQL = "units.id AS id,units_sections.section_id, units.strat_name, mbr_name Mbr, fm_name Fm, gp_name Gp, sgp_name SGp, era, period, max_thick,min_thick, color, lith_class, lith_type, lith_short lith, environ_class, environ_type, environ, count(distinct collection_no) pbdb, FO_interval, FO_h, FO_age, b_age, LO_interval, LO_h, LO_age, t_age, position_bottom, notes";
                  
              var sql = "SELECT " + ((req.query.response === "long") ? longSQL : shortSQL) + " FROM units \
                  JOIN units_sections ON units_sections.unit_id = units.id \
                  JOIN lookup_unit_liths ON lookup_unit_liths.unit_id=units.id \
                  JOIN lookup_unit_intervals ON units.id=lookup_unit_intervals.unit_id \
                  LEFT JOIN unit_strat_names ON unit_strat_names.unit_id=units.id \
                  LEFT JOIN lookup_strat_names ON lookup_strat_names.strat_name_id=unit_strat_names.strat_name_id \
                  " + ((req.query.response === "long") ? "LEFT JOIN unit_notes ON unit_notes.unit_id=units.id" : "") + " \
                  LEFT JOIN pbdb_matches ON pbdb_matches.unit_id=units.id \
                  WHERE units_sections.col_id = ? \
                  GROUP BY units.id ORDER BY t_age ASC";

              var query = larkin.query(sql, [column.col_id], function(error, result) {
                if (error) {
                  callbackB(error);
                } else {
                  callbackB(null, column, column_info, result);
                }
              });
            }
          ],
          // after the two queries are executed, send the result
          function(err, column, column_info, result) {
            if (err) {
              callback(err);
            } else {
              var col = [column_info];
              if (geo) {
                col[0].geometry = gp(wellknown(column.wkt),6);
              }
              col[0].units = result;
              callback(null, col[0]);
            }
          });
        } else {
          callback(null);
        }
      }
    }, function(error, results) {
      if (error) {
        larkin.error(req, res, next, "Something went wrong");
      } else {
        larkin.sendData(results, res, "json", next);
      }
    });
  }
}
