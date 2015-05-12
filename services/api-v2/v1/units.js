var api = require("./api"),
    async = require("async"),
    dbgeo = require("dbgeo"),
    gp = require("geojson-precision"),
    larkin = require("./larkin");

module.exports = function(req, res, next) {
  // If no parameters, send the route definition
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }
  // First determine age range component of query, if any. 
  // NB: ORDER MATTERS here. Do NOT add else if statements before req.query.interval_name, req.query.age or req.query.age_top else statements or  those age parameters will be ommitted 
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
        });
      } else if (req.query.age) {
        callback(null, {"interval_name": "none", "age_bottom": req.query.age, "age_top": req.query.age});
      } else if (req.query.age_top && req.query.age_bottom) {
        callback(null, {"interval_name": "none", "age_bottom": req.query.age_bottom, "age_top": req.query.age_top});
      } else if (req.query.strat_name) {
        larkin.query("SELECT strat_name_id FROM lookup_strat_names WHERE strat_name LIKE ? ", ["%" + req.query.strat_name + "%"], function(error, result) {
          if (error) {
            callback(error);
          } else {
            if (result.length === 0) {
              larkin.error(req, res, next, "No results found");
            } else {
              var ids = result.map(function(d) { return d.strat_name_id });
              callback(null, {"interval_name": "none", "age_bottom": 99999, "age_top": 0, "strat_ids": ids });
            }
          }
        });

      } else if (req.query.strat_id) {
        var ids = req.query.strat_id.split(",").map(function(d) { return parseInt(d) });
        callback(null, {"interval_name": "none", "age_bottom": 99999, "age_top": 0, "strat_ids": ids });
      } else if (req.query.id || req.query.section_id || req.query.col_id || req.query.lith || req.query.lith_class || req.query.lith_type || req.query.environ || req.query.environ_class || req.query.environ_type) { 
        callback(null, {"interval_name": "none", "age_bottom": 99999, "age_top": 0});
      } else {
        callback("error");
      }
    },
  
    function(data, callback) {

      var where = "",
          orderby = [],
          params = [];

      if (req.query.lith || req.query.lith_class || req.query.lith_type) {
        where += " AND units.id IN (SELECT unit_liths.unit_id from unit_liths JOIN liths on lith_id=liths.id WHERE ?? LIKE ?) ";

        if (req.query.lith) {
          params.push(req.query.lith, "lith");
        } else if (req.query.lith_class) {
          params.push(req.query.lith_class, "lith_class");
        } else if (req.query.lith_type) {
          params.push(req.query.lith_type, "lith_type");
        } 
      }

      if (data.age_bottom !== 99999) {
        where += " AND FO_age > ? AND LO_age < ?";
        params.push(data.age_top, data.age_bottom);
      }

      if (req.query.id) {
        if (req.query.id.indexOf(",") > -1) {
          var ids = req.query.id.split(","),
              placeholders = [];
          
          ids = ids.map(function(d) {
            return parseInt(d);
          });

          for (var i = 0; i < ids.length; i++) {
            placeholders.push("?");
            params.push(ids[i]);
          }

          where += " AND units_sections.unit_id IN (" + placeholders.join(",") + ")";
          orderby.push("FIELD(units.id, " + ids.join(",") + ")");

        } else {
          where += " AND units_sections.unit_id = ?";
          params.push(req.query.id);
        }
      }

      if (req.query.section_id) {
        if (req.query.section_id.indexOf(",") > -1) {
          var sections = req.query.section_id.split(","),
              placeholders = [];

          for (var i = 0; i < sections.length; i++) {
            placeholders.push("?");
            params.push(sections[i]);
          }

          where += " AND units_sections.section_id IN (" + placeholders.join(",") + ")";
          orderby.push("FIELD(units_sections.section_id, " + sections.join(",") + ")");
        } else {
          where += " AND units_sections.section_id = ?";
          params.push(req.query.section_id);
        }
      }

      if (req.query.col_id) {
        if (req.query.col_id.indexOf(",") > -1) {
          var cols = req.query.col_id.split(","),
              placeholders = [];

          for (var i = 0; i < cols.length; i++) {
            placeholders.push("?");
            params.push(cols[i]);
          }

          where += " AND units_sections.col_id IN (" + placeholders.join(",") + ")";
          orderby.push("FIELD(units_sections.col_id, " + cols.join(",") + ")");
        } else {
          where += " AND units_sections.col_id = ?";
          params.push(req.query.col_id);
        }
      }

      if (req.query.strat_name || req.query.strat_id) {
        where += " AND (lookup_strat_names.bed_id IN (?) OR lookup_strat_names.mbr_id IN (?) OR lookup_strat_names.fm_id IN (?) OR lookup_strat_names.gp_id IN (?) OR lookup_strat_names.sgp_id IN (?)) ";
        params.push(data.strat_ids, data.strat_ids, data.strat_ids, data.strat_ids, data.strat_ids);
      }

      if (req.query.project_id) {
        where += " AND cols.project_id = ?";
        params.push(req.query.project_id);
      }

      var environ = "", 
          environ_field = "";
      if (req.query.environ) {
        environ = req.query.environ;
        environ_field = "environs.environ";
      } else if (req.query.environ_class) {
        environ = req.query.environ_class;
        environ_field = "environs.environ_class";
      } else if (req.query.environ_type) {
        environ = req.query.environ_type;
        environ_field = "environs.environ_type";
      }
      if (environ !== ""){
        where += " AND ?? LIKE ?";
        params.push(environ_field, environ);
      } 

      var shortSQL = "units.id AS id,units_sections.section_id as section_id, units_sections.col_id as col_id, col_area, units.strat_name, units.position_bottom, unit_strat_names.strat_name_id, mbr_name Mbr, fm_name Fm, gp_name Gp, sgp_name SGp, era, period, max_thick, min_thick, color AS u_color, lith_type, count(distinct collection_no) pbdb";
            
      var longSQL = "units.id AS id, units_sections.section_id as section_id, project_id, units_sections.col_id as col_id, col_area, units.strat_name, unit_strat_names.strat_name_id, mbr_name Mbr, fm_name Fm, gp_name Gp, sgp_name SGp, era, period, max_thick,min_thick, lith_class, lith_type, lith_long lith, lookup_unit_liths.environ_class, lookup_unit_liths.environ_type, lookup_unit_liths.environ, count(distinct collection_no) pbdb, FO_interval, FO_h, FO_age, LO_interval, LO_h, LO_age, position_bottom, notes, units.color AS u_color, colors.unit_hex AS color, colors.text_hex AS text_color, min(ubt.t1_age) AS t_age, GROUP_CONCAT(distinct ubt.unit_id_2 SEPARATOR '|') AS units_above, max(ubb.t1_age) AS b_age, GROUP_CONCAT(distinct ubb.unit_id SEPARATOR '|') AS units_below"; 

      var unitBoundariesJoin = (req.query.debug === "true") ? "LEFT JOIN unit_boundaries_scratch ubb ON ubb.unit_id_2=units.id LEFT JOIN unit_boundaries_scratch ubt ON ubt.unit_id=units.id" : "LEFT JOIN unit_boundaries ubb ON ubb.unit_id_2=units.id LEFT JOIN unit_boundaries ubt ON ubt.unit_id=units.id";

      var geometry = ((req.query.format && api.acceptedFormats.geo[req.query.format]) || req.query.response === "long") ? ", cols.lat AS clat, cols.lng AS clng, ubt.paleo_lat AS t_plat, ubt.paleo_lng AS t_plng, ubb.paleo_lat AS b_plat, ubb.paleo_lng AS b_plng " : "";

      var sql = "SELECT " + ((req.query.response === "long") ? longSQL : shortSQL) + geometry + " FROM units \
            JOIN units_sections ON units_sections.unit_id=units.id \
            JOIN cols ON units_sections.col_id=cols.id \
            JOIN lookup_unit_liths ON lookup_unit_liths.unit_id=units.id \
            JOIN lookup_unit_intervals ON units.id=lookup_unit_intervals.unit_id \
            " + unitBoundariesJoin + " \
            LEFT JOIN unit_strat_names ON unit_strat_names.unit_id=units.id \
            LEFT JOIN lookup_strat_names ON lookup_strat_names.strat_name_id=unit_strat_names.strat_name_id \
            " + ((req.query.response === "long") ? "LEFT JOIN unit_notes ON unit_notes.unit_id=units.id JOIN colors ON units.color = colors.color" : "") + " \
            LEFT JOIN pbdb_matches ON pbdb_matches.unit_id=units.id \
            " + ((environ !== "") ? "LEFT JOIN unit_environs ON units.id=unit_environs.unit_id LEFT JOIN environs ON unit_environs.environ_id=environs.id" : "") + " \
            WHERE status_code='active' " + where + " GROUP BY units.id ORDER BY " + ((orderby.length > 0) ? (orderby.join(", ") + ", t_age ASC") : "t_age ASC");
     
      larkin.query(sql, params, function(error, result) {
          if (error) {
            console.log(error);
            callback(error);
          } else {
            if (req.query.response === "long" && req.query.format !== "csv") {
              result.forEach(function(d) {
                d.units_above = larkin.jsonifyPipes(d.units_above, "integers");
                d.units_below = larkin.jsonifyPipes(d.units_below, "integers");
              });
            }

            if (req.query.format && api.acceptedFormats.geo[req.query.format]) {
              var geomAge = (req.query.geom_age && req.query.geom_age === "top") ? ["t_plat", "t_plng"] : (req.query.geom_age === "bottom") ? ["b_plat", "b_plng"] : ["clat", "clng"];

              dbgeo.parse({
                "data": result,
                "geometryType": "ll",
                "geometryColumn": geomAge,
                "outputFormat": larkin.getOutputFormat(req.query.format),
                "callback": function(error, output) {
                  if (error) {
                    larkin.error(req, res, next, "An error was incurred during conversion");
                  } else {
                    if (larkin.getOutputFormat(req.query.format) === "geojson") {
                      output = gp(output, 4);
                    }
                    callback(null, data, output);
                  }
                }
              });
            } else {
              callback(null, data, result);
            }
          }
      });
    }
  ], function(error, data, result) {
    if (error) {
      larkin.error(req, res, next, "Something went wrong");
    } else {
      if (api.acceptedFormats.bare[req.query.format]) {
        larkin.sendBare(result, res, next);
      } else {
        larkin.sendCompact(result, res, (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json", next);
      }
    }
  });
}
