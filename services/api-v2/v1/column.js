var api = require("./api"),
    larkin = require("./larkin"),
    wellknown = require("wellknown"),
    async = require("async");

module.exports = function(req, res, next) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }
  
  if (isFinite(req.query.id) || isFinite(req.query.lat) && isFinite(req.query.lng)) {
    async.waterfall([
      function(callback) {
        if (req.query.lat) {
          // Find nearest column
          larkin.query("SELECT col_id from col_areas JOIN cols on col_id=cols.id WHERE ST_CONTAINS(col_areas.col_area,ST_GEOMFROMTEXT('POINT(? ?)')) and status_code='active'", [parseFloat(req.query.lng), parseFloat(req.query.lat)], function(error, result) {
            if (error) {
              callback(error);
            } else {
              if (result.length < 1) {
                callback("No columns found");
              } else if (result.length > 1) {
                callback("More than 1 column found");
              } else {
                callback(null, result[0].col_id);
              }
            }
          });
        } else {
          callback(null, req.query.id);
        }
      },

      function(column_id, callback) {
        if (req.query.geom === "true") {
          var sql = "SELECT c.id, col_name, asText(ca.col_area) AS geom FROM cols c JOIN col_areas ca ON c.id = ca.col_id WHERE c.id = ?"
        } else {
          var sql = "SELECT id, col_name FROM cols WHERE id = ?";
        }
        larkin.query(sql, [column_id], function(error, result) {
          if (error) {
            callback(error);
          } else {
            if (result.length === 0) {
              larkin.error(req, res, next, "No results found.");
            } else {
              callback(null, column_id, result[0]);
            }
          }
        });
      },

      function(column_id, column_info, callback) {
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

        var query = larkin.query(sql, [column_id], function(error, result) {
          if (error) {
            callback(error);
          } else {
            callback(null, column_info, result);
          }
        });
      }
    ],
    // after the two queries are executed, send the result
    function(err, column_info, result) {
      if (err) {
        larkin.error(req, res, next, "An error was incurred");
      } else {
        var column = [column_info];
        column[0].units = result;
        var format = "json";
        if (req.query.geom === "true") {
          column_info.geom = wellknown(column_info.geom);
        }
        larkin.sendData(column, res, format, next);
      }
    });

  } else {
    larkin.error(req, res, next, "An invalid parameter value was given");
  }
}
