var api = require("./api"),
    async = require("async"),
    larkin = require("./larkin");

module.exports = function(req, res, next) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }
  async.waterfall([
    function(callback) {
      if (req.query.interval_name) {
        larkin.query("SELECT age_bottom,age_top,interval_name from intervals where interval_name = ? LIMIT 1", [req.query.interval_name], function(error, result) {
          if (error) {
            callback(error);
          } else {
            if (result.length === 0) {
              larkin.error(req, res, next, "No results found");
            } else {
              callback(null, {"interval_name": result[0].interval_name, "age_bottom": result[0].age_bottom, "age_top": result[0].age_top});
              }
            }
          }
        );
      } else if (req.query.age) {
        callback(null, {"interval_name": "Unknown", "age_bottom": req.query.age, "age_top": req.query.age});
      } else if (req.query.age_top && req.query.age_bottom) {
        callback(null, {"interval_name": "Unknown", "age_bottom": req.query.age_bottom, "age_top": req.query.age_top});
      } else if (req.query.section_id) { 
        callback(null, {"interval_name": "Unknown", "age_bottom": 99999, "age_top": 0});
      } else {
        callback("error");
      }
    },
    function(data, callback) {
      var lith = '%',
          lith_field = 'lith';
      if (req.query.lith){
        lith = req.query.lith;
      } else if (req.query.lith_class){
        lith = req.query.lith_class;
        lith_field = 'lith_class';
      } else if (req.query.lith_type){
        lith = req.query.lith_type;
        lith_field = 'lith_type';
      }

      var where = "",
          params = [data.age_top, data.age_bottom];

      if (req.query.section_id) {
        where += " AND units.section_id = ?";
        params.push(req.query.section_id);
      }

      if (req.query.col_id) {
        where += " AND units.col_id = ?";
        params.push(req.query.col_id);
      }

      var shortSQL = "units.id AS id,units_sections.section_id as section_id, units_sections.col_id as col_id, col_area, units.strat_name, units.position_bottom, mbr_name Mbr, fm_name Fm, gp_name Gp, sgp_name SGp, era, period, max_thick, min_thick, color AS u_color, lith_type, count(distinct collection_no) pbdb";
            
      var longSQL = "units.id AS id, units_sections.section_id as section_id, project_id, units_sections.col_id as col_id, col_area, units.strat_name, mbr_name Mbr, fm_name Fm, gp_name Gp, sgp_name SGp, era, period, max_thick,min_thick, lith_class, lith_type, lith_long lith, environ_class, environ_type, environ, count(distinct collection_no) pbdb, FO_interval, FO_h, FO_age, max(ubb.t1_age) AS b_age, LO_interval, LO_h, LO_age, min(ubt.t1_age) AS t_age, position_bottom, notes, units.color AS u_color, colors.unit_hex AS color, colors.text_hex AS text_color"; 

      var sql = "SELECT " + ((req.query.response === "long") ? longSQL : shortSQL) + " FROM units \
            JOIN units_sections ON units_sections.unit_id=units.id \
            JOIN cols ON units_sections.col_id=cols.id \
            JOIN lookup_unit_liths ON lookup_unit_liths.unit_id=units.id \
            JOIN lookup_unit_intervals ON units.id=lookup_unit_intervals.unit_id \
            LEFT JOIN unit_boundaries ubb ON ubb.unit_id_2=units.id \
            LEFT JOIN unit_boundaries ubt ON ubt.unit_id=units.id \
            LEFT JOIN unit_strat_names ON unit_strat_names.unit_id=units.id \
            LEFT JOIN lookup_strat_names ON lookup_strat_names.strat_name_id=unit_strat_names.strat_name_id \
            " + ((req.query.response === "long") ? "LEFT JOIN unit_notes ON unit_notes.unit_id=units.id JOIN colors ON units.color = colors.color" : "") + " \
            LEFT JOIN pbdb_matches ON pbdb_matches.unit_id=units.id \
            WHERE status_code='active' AND FO_age > ? AND LO_age < ? AND units.id IN (SELECT unit_liths.unit_id from unit_liths JOIN liths on lith_id=liths.id WHERE lith like " + lith_field + ")" + where + " GROUP BY units.id ORDER BY units.position_bottom ASC";
     
      larkin.query(sql, params, function(error, result) {
          if (error) {
            callback(error);
          } else {
            callback(null, data, result);
          }
      });
    }
  ], function(error, data, result) {
    if (error) {
      larkin.error(req, res, next, "Something went wrong");
    } else {
      larkin.sendData(result, res, (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json", next);
    }
  });
}
