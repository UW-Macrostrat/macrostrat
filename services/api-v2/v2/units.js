var api = require("./api"),
    async = require("async"),
    dbgeo = require("dbgeo"),
    gp = require("geojson-precision"),
    larkin = require("./larkin");

function findNumberInString(obj){
  var matches = obj.replace(/,/g, '').match(/(\+|-)?((\d+(\.\d+)?)|(\.\d+))/);
  return matches && matches[0] || null;
}

function fixLiths(obj) {
  return obj.split("|").map(function(d) {
    var prop = parseFloat(findNumberInString(d)),
        type = d.replace(prop, "").replace(/\.\d+/, '').trim();

    return {"type": type, "prop": prop}
  });
}

function pipifyLiths(data) {
  var piped = data.map(function(d) {
    return d.type + " - " + d.prop;
  }).join("|");
  return piped;
}

module.exports = function(req, res, next, cb) {
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
              return larkin.error(req, res, next, "No results found");
            } else {
              callback(null, {"interval_name": result[0].interval_name, "age_bottom": result[0].age_bottom, "age_top": result[0].age_top});
            }
          }
        });

      } else if (req.query.age) {
        callback(null, {"interval_name": "none", "age_bottom": req.query.age, "age_top": req.query.age});

      } else if (req.query.age_top && req.query.age_bottom) {
        callback(null, {"interval_name": "none", "age_bottom": req.query.age_bottom, "age_top": req.query.age_top});

      } else if (req.query.lat && req.query.lng) {
        var sql = (req.query.adjacents === "true") ? "WITH containing_geom AS (SELECT poly_geom FROM macrostrat.cols WHERE ST_Contains(poly_geom, ST_GeomFromText($1, 4326))) SELECT id FROM macrostrat.cols WHERE ST_Intersects((SELECT * FROM containing_geom), poly_geom) ORDER BY ST_Distance(ST_Centroid(poly_geom), ST_GeomFromText($1, 4326))" : "SELECT id FROM macrostrat.cols WHERE ST_Contains(poly_geom, st_setsrid(ST_GeomFromText($1), 4326)) ORDER BY ST_Distance(ST_Centroid(poly_geom), ST_GeomFromText($1, 4326))";
        
        larkin.queryPg("geomacro", sql, ["POINT(" + req.query.lng + " " + req.query.lat + ")"], function(error, response) {
          if (error) {
            callback(error);
          } else {
            callback(null, {"interval_name": "none", "age_bottom": 99999, "age_top": 0, "col_ids": response.rows.map(function(d) { return d.id })});
          }
        });

      } else if (req.query.col_id && req.query.adjacents) {
        var col_ids = larkin.parseMultipleIds(req.query.col_id),
            placeholders = col_ids.map(function(d, i) { return "$" + (i + 1)});

        var sql = "WITH containing_geom AS (SELECT poly_geom FROM macrostrat.cols WHERE id IN (" + placeholders.join(",") + ")) SELECT id FROM macrostrat.cols WHERE ST_Intersects((SELECT * FROM containing_geom), poly_geom)";
  
        if (col_ids.length === 1) {
          sql += " ORDER BY ST_Distance(ST_Centroid(poly_geom), (SELECT * FROM containing_geom))"
        }
        
        larkin.queryPg("geomacro", sql, col_ids, function(error, response) {
          if (error) {
            callback(error);
          } else {
            callback(null, {"interval_name": "none", "age_bottom": 99999, "age_top": 0, "col_ids": response.rows.map(function(d) { return d.id })});
          }
        });


      } else if (req.query.strat_name) {
        larkin.query("SELECT strat_name_id FROM lookup_strat_names WHERE strat_name LIKE ? ", ["%" + req.query.strat_name + "%"], function(error, result) {
          if (error) {
            callback(error);
          } else {
            if (result.length === 0) {
              return larkin.error(req, res, next, "No results found");
            } else {
              var ids = result.map(function(d) { return d.strat_name_id });
              callback(null, {"interval_name": "none", "age_bottom": 99999, "age_top": 0, "strat_ids": ids });
            }
          }
        });

      } else if (req.query.strat_name_id) {
        var ids = larkin.parseMultipleIds(req.query.strat_name_id);
        callback(null, {"interval_name": "none", "age_bottom": 99999, "age_top": 0, "strat_ids": ids });

      } else if (req.query.unit_id || req.query.section_id || req.query.col_id || req.query.lith || req.query.lith_class || req.query.lith_type || req.query.environ || req.query.environ_class || req.query.environ_type || req.query.project_id) { 
        callback(null, {"interval_name": "none", "age_bottom": 99999, "age_top": 0});

      } else {
        callback("error");
      }
    },
  
    function(data, callback) {

      var where = "",
          orderby = [],
          params = {};

      if (req.query.lith || req.query.lith_class || req.query.lith_type) {
        where += " AND units.id IN (SELECT unit_liths.unit_id from unit_liths JOIN liths on lith_id=liths.id WHERE ::lith_field LIKE :lith) ";

        if (req.query.lith) {
          params["lith_field"] = "lith";
          params["lith"] = req.query.lith;

        } else if (req.query.lith_class) {
          params["lith_field"] = "lith_class";
          params["lith"] = req.query.lith_class;

        } else if (req.query.lith_type) {
          params["lith_field"] = "lith_type";
          params["lith"] = req.query.lith_type;
        } 
      }

      if (data.age_bottom !== 99999) {
        where += " AND FO_age > :age_top AND LO_age < :age_bottom";
        params["age_top"] = data.age_top;
        params["age_bottom"] = data.age_bottom;
      }

      if (req.query.unit_id) {
        where += " AND units_sections.unit_id IN (:unit_ids)"
        params["unit_ids"] = larkin.parseMultipleIds(req.query.unit_id);
        orderby.push("FIELD(units.id, " + larkin.parseMultipleIds(req.query.unit_id).join(",") + ")");
      }

      if (req.query.section_id) {
        where += " AND units_sections.section_id IN (:section_ids)";
        params["section_ids"] = larkin.parseMultipleIds(req.query.section_id);
      }

      if ("col_ids" in data) {
        where += " AND units_sections.col_id IN (:col_ids)";
        params["col_ids"] = data.col_ids;
      } else if (req.query.col_id) {
        where += " AND units_sections.col_id IN (:col_ids)";
        params["col_ids"] = larkin.parseMultipleIds(req.query.col_id);
      } 

      if (data.strat_ids) {
        where += " AND (lookup_strat_names.bed_id IN (:strat_ids) OR lookup_strat_names.mbr_id IN (:strat_ids) OR lookup_strat_names.fm_id IN (:strat_ids) OR lookup_strat_names.gp_id IN (:strat_ids) OR lookup_strat_names.sgp_id IN (:strat_ids)) ";
        params["strat_ids"] = data.strat_ids;
      }

      if (req.query.project_id) {
        where += " AND cols.project_id IN (:project_id)";
        params["project_id"] = larkin.parseMultipleIds(req.query.project_id);
      }

      if (req.query.environ) {
        params["environ"] = req.query.environ;
        params["environ_field"] = "environs.environ";
 
      } else if (req.query.environ_class) {
        params["environ"] = req.query.environ_class;
        params["environ_field"] = "environs.environ_class";

      } else if (req.query.environ_type) {
        params["environ"] = req.query.environ_type;
        params["environ_field"] = "environs.environ_type";

      }
      if ("environ" in params) {
        where += " AND ::environ_field LIKE :environ";
      } 

      var shortSQL = "units.id AS unit_id,units_sections.section_id as section_id, units_sections.col_id as col_id, col_area, units.strat_name, unit_strat_names.strat_name_id, mbr_name Mbr, fm_name Fm, gp_name Gp, sgp_name SGp, era, period, max_thick, min_thick, lith_type, count(distinct collection_no) pbdb_collections";
            
      var longSQL = "units.id AS unit_id, units_sections.section_id as section_id, project_id, units_sections.col_id as col_id, col_area, units.strat_name, unit_strat_names.strat_name_id, mbr_name Mbr, fm_name Fm, gp_name Gp, sgp_name SGp, era, period, max_thick,min_thick, lith_class, lith_type, lith_long lith, lookup_unit_liths.environ_class, lookup_unit_liths.environ_type, lookup_unit_liths.environ, count(distinct collection_no) pbdb_collections, notes, colors.unit_hex AS color, colors.text_hex AS text_color, ubt.t1 as t_int_id, LO_interval AS t_int_name, LO_age AS t_int_age, min(ubt.t1_age) AS t_age, ubt.t1_prop as t_prop, GROUP_CONCAT(distinct ubt.unit_id_2 SEPARATOR '|') AS units_above, ubb.t1 AS b_int_id, FO_interval AS b_int_name, FO_age AS b_int_age, max(ubb.t1_age) AS b_age, ubb.t1_prop as b_prop, GROUP_CONCAT(distinct ubb.unit_id SEPARATOR '|') AS units_below"; 

      var unitBoundariesJoin = (req.query.debug === "true") ? "LEFT JOIN unit_boundaries_scratch ubb ON ubb.unit_id_2=units.id LEFT JOIN unit_boundaries_scratch ubt ON ubt.unit_id=units.id" : "LEFT JOIN unit_boundaries ubb ON ubb.unit_id_2=units.id LEFT JOIN unit_boundaries ubt ON ubt.unit_id=units.id";

      var geometry = ((req.query.format && api.acceptedFormats.geo[req.query.format]) || req.query.response === "long") ? ", cols.lat AS clat, cols.lng AS clng, ubt.paleo_lat AS t_plat, ubt.paleo_lng AS t_plng, ubb.paleo_lat AS b_plat, ubb.paleo_lng AS b_plng " : "";

      var sql = "SELECT " + ((req.query.response === "long" || cb) ? longSQL : shortSQL) + geometry + " FROM units \
            JOIN units_sections ON units_sections.unit_id=units.id \
            JOIN cols ON units_sections.col_id=cols.id \
            JOIN lookup_unit_liths ON lookup_unit_liths.unit_id=units.id \
            JOIN lookup_unit_intervals ON units.id=lookup_unit_intervals.unit_id \
            " + unitBoundariesJoin + " \
            LEFT JOIN unit_strat_names ON unit_strat_names.unit_id=units.id \
            LEFT JOIN lookup_strat_names ON lookup_strat_names.strat_name_id=unit_strat_names.strat_name_id \
            " + ((req.query.response === "long" || cb) ? "LEFT JOIN unit_notes ON unit_notes.unit_id=units.id JOIN colors ON units.color = colors.color" : "") + " \
            LEFT JOIN pbdb_matches ON pbdb_matches.unit_id=units.id \
            " + (("environ" in params) ? "LEFT JOIN unit_environs ON units.id=unit_environs.unit_id LEFT JOIN environs ON unit_environs.environ_id=environs.id" : "") + " \
            WHERE status_code='active' " + where + " GROUP BY units.id ORDER BY " + ((orderby.length > 0) ? (orderby.join(", ") + ", t_age ASC") : "t_age ASC");
     
      larkin.query(sql, params, function(error, result) {
          if (error) {
            console.log(error);
            callback(error);
          } else {
            if (req.query.response === "long") {
              result.forEach(function(d) {
                d.units_above = larkin.jsonifyPipes(d.units_above, "integers");
                d.units_below = larkin.jsonifyPipes(d.units_below, "integers");
                d.lith_class = fixLiths(d.lith_class);
                d.lith_type = fixLiths(d.lith_type);
                d.lith = fixLiths(d.lith);
              });
            } else {
              result.forEach(function(d) {
                d.lith_type = fixLiths(d.lith_type);
              });
            }

            if (req.query.format === "csv" && req.query.response === "long" && !cb) {
              result.forEach(function(d) {
                d.units_above = d.units_above.join(",");
                d.units_below = d.units_below.join(",");
                d.lith_class = pipifyLiths(d.lith_class);
                d.lith_type = pipifyLiths(d.lith_type);
                d.lith = pipifyLiths(d.lith);
              });
            }

            if (req.query.format && api.acceptedFormats.geo[req.query.format] && !cb) {
              var geomAge = (req.query.geom_age && req.query.geom_age === "top") ? ["t_plat", "t_plng"] : (req.query.geom_age === "bottom") ? ["b_plat", "b_plng"] : ["clat", "clng"];

              dbgeo.parse({
                "data": result,
                "geometryType": "ll",
                "geometryColumn": geomAge,
                "outputFormat": larkin.getOutputFormat(req.query.format),
                "callback": function(error, output) {
                  if (error) {
                    return larkin.error(req, res, next, "An error was incurred during conversion");
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
      console.log(error);
      return larkin.error(req, res, next, "Something went wrong");
    } else {
      if (cb) {
        cb(result);
      } else if (api.acceptedFormats.bare[req.query.format]) {
        return larkin.sendBare(result, res, next);
      } else {
        return larkin.sendCompact(result, res, (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json", next);
      }
    }
  });
}
