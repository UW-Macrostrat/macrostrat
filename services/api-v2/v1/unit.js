var api = require("./api"),
    async = require("async"),
    larkin = require("./larkin");

module.exports = function(req, res, next) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }
  // Use some control flow, as we might need two separate queries for the result
  async.waterfall([
    function(callback) {
      // If pbdb colllections are requested, go get those first
      if (req.query.pbdb && isFinite(req.query.id)) {
        var sql = "SELECT pbdb.collections.collection_name, pbdb_matches.collection_no FROM pbdb_matches JOIN pbdb.collections USING (collection_no) where unit_id = ? and pbdb.collections.release_date<=now()";
        larkin.query(sql, [req.query.id ], function(error, collections) {
          // When we have the collections, move on to the next function in the waterfall
          callback(null, collections);
        });
      } else {
        // If we don't need collections, move on
        callback(null, null);
      }
    },

    function(collections, callback) {
      if (isFinite(req.query.id)) {
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
              WHERE units.id = ?";
        larkin.query(sql, [req.query.id], function(error, data) {
          // Once we have the unit data, move on to the final function
          callback(null, collections, data);
        });
      } else { 
        // If no unit ID was provided, feed the user the standard route error
        callback("error");
      }
    }
  ], function(error, collections, unit) {
    if (error) {
      larkin.error(req, res, next, "Something went wrong");
    } else {
      // If the user asked for pbdb collections, add them as an attribute of the unit
      if (collections) {
        unit[0].pbdb_collections = collections;
      }
      // Finally, send the result
      larkin.sendData(unit, res, (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json", next);
    }
  });
}
