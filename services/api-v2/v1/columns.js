var api = require("./api"),
    async = require("async"),
    dbgeo = require("dbgeo"),
    gp = require("geojson-precision"),
    larkin = require("./larkin");

module.exports = function(req, res, next) {
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
              callback("No results found");
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
      } else if (req.query.hasOwnProperty("all")) {
        callback(null, {"interval_name": "Unknown", "age_bottom": 9999, "age_top": 0});
      } else if (req.query.lith_type || req.query.lith_class || req.query.lith || req.query.col_group_id || req.query.col_group || req.query.unit_id) {
        callback(null, {"interval_name": "Unknown", "age_bottom": 9999, "age_top": 0});
      } else if (req.query.col_id) {
        if (req.query.adjacents === "true") {
          larkin.queryPg("geomacro", "WITH containing_geom AS (SELECT poly_geom FROM macrostrat.cols WHERE id = $1) select id from macrostrat.cols where ST_Intersects((SELECT * FROM containing_geom), poly_geom)", [req.query.col_id], function(error, response) {
            if (error) {
              callback(error);
            } else {
              callback(null, {"interval_name": "Unknown", "age_bottom": 9999, "age_top": 0, "col_ids": response.rows.map(function(d) { return d.id })});
            }
          })
        } else {
          callback(null, {"interval_name": "Unknown", "age_bottom": 9999, "age_top": 0, "col_ids": req.query.col_id.split(",")});
        }
        
      } else if (isFinite(req.query.lat) && isFinite(req.query.lng)) {

        var sql = (req.query.adjacents === "true") ? "WITH containing_geom AS (SELECT poly_geom FROM macrostrat.cols WHERE ST_Contains(poly_geom, st_setsrid(ST_GeomFromText($1), 4326))) select id from macrostrat.cols where ST_Intersects((SELECT * FROM containing_geom), poly_geom)" : "SELECT id FROM macrostrat.cols WHERE ST_Contains(poly_geom, st_setsrid(ST_GeomFromText($1), 4326))";
        
        larkin.queryPg("geomacro", sql, ["POINT(" + req.query.lng + " " + req.query.lat + ")"], function(error, response) {
          if (error) {
            callback(error);
          } else {
            callback(null, {"interval_name": "Unknown", "age_bottom": 9999, "age_top": 0, "col_ids": response.rows.map(function(d) { return d.id })});
          }
        });

      } else {
        larkin.error(req, res, next, "An invalid parameter was given");
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

      var geo = (req.query.format && api.acceptedFormats.geo[req.query.format]) ? "AsWKT(col_areas.col_area) AS wkt," : "",
          stratJoin = "",
          first_where = "",
          where = "",
          orderby = "",
          params = [lith_field, lith, lith_field, lith];

      if (data.age_bottom !== 99999) {
        first_where += " AND FO_age > ? AND LO_age < ?";
        where += " AND FO_age > ? AND LO_age < ?";
        params.push(data.age_top, data.age_bottom, data.age_top, data.age_bottom);
      }

      if (req.query.strat_name || req.query.strat_id) {
        where += " AND (lookup_strat_names.bed_id IN (?) OR lookup_strat_names.mbr_id IN (?) OR lookup_strat_names.fm_id IN (?) OR lookup_strat_names.gp_id IN (?) OR lookup_strat_names.sgp_id IN (?) )";
        params.push(data.strat_ids, data.strat_ids, data.strat_ids, data.strat_ids, data.strat_ids);

        stratJoin += "LEFT JOIN unit_strat_names ON unit_strat_names.unit_id=units.id LEFT JOIN lookup_strat_names ON lookup_strat_names.strat_name_id=unit_strat_names.strat_name_id ";
      }

      if (req.query.col_group_id) {
        where += " AND col_groups.id = ?";
        params.push(req.query.col_group_id);
      }

      if (req.query.col_group) {
        where += " AND col_groups.col_group = ?";
        params.push(req.query.col_group);
      }

      if (req.query.unit_id) {
        if (req.query.unit_id.indexOf(",") > -1) {
          var ids = req.query.unit_id.split(","),
              placeholders = [];
          
          ids = ids.map(function(d) {
            return parseInt(d);
          });

          for (var i = 0; i < ids.length; i++) {
            placeholders.push("?");
            params.push(ids[i]);
          }

          where += " AND units.id IN (" + placeholders.join(",") + ")";
        } else {
          where += " AND units.id = ?";
          params.push(req.query.unit_id);
        }
      }

      if (data.col_ids) {
        where += " AND col_areas.col_id IN (?)";
        params.push(data.col_ids);
      }

      if (req.query.project_id) {
        where += " AND cols.project_id = ?";
        params.push(req.query.project_id);
      }

      var additionalFields = (req.query.response === "long") ? "col_name, col_group, col_groups.id AS col_group_id, max(lookup_unit_intervals.b_age) AS b_age, min(lookup_unit_intervals.t_age) AS t_age, GROUP_CONCAT(DISTINCT units_sections.section_id SEPARATOR '|') AS sections, count(distinct pbdb_matches.id) AS pbdb_collections, sum(pbdb_matches.occs) AS pbdb_occs, " : "";

      var additionalJoins = (req.query.response === "long") ? " LEFT OUTER JOIN pbdb_matches ON pbdb_matches.unit_id = units.id" : ""

      larkin.query("SELECT " + geo + " col_areas.col_id, " + additionalFields + "round(cols.col_area, 1) AS area, GROUP_CONCAT(units.id SEPARATOR '|') AS units, sum(max_thick) max_thick, sum(min_thick) min_thick, sum(LT.cpm) lith_max_thick, sum(LT.cpl) lith_min_thick,  LT2.lts lith_types \
        FROM col_areas \
        JOIN cols ON cols.id = col_areas.col_id \
        JOIN units_sections ON units_sections.col_id = cols.id \
        JOIN units ON unit_id = units.id \
        JOIN col_groups ON col_groups.id = cols.col_group_id \
        " + additionalJoins + " \
        JOIN lookup_unit_intervals ON lookup_unit_intervals.unit_id = units_sections.unit_id \
        JOIN (SELECT unit_id, round(sum(comp_prop*max_thick), 1) cpm, round(sum(comp_prop*min_thick), 1) cpl FROM unit_liths JOIN liths on lith_id=liths.id JOIN units on unit_id=units.id WHERE ?? like ? GROUP BY unit_id) LT ON LT.unit_id=units.id \
        " + stratJoin + " \
        JOIN (SELECT col_id, GROUP_CONCAT(distinct lith_type SEPARATOR '|') lts from liths JOIN unit_liths on lith_id=liths.id JOIN units_sections ON unit_liths.unit_id=units_sections.unit_id JOIN lookup_unit_intervals ON lookup_unit_intervals.unit_id=units_sections.unit_id WHERE ?? like ? " + first_where + " GROUP BY col_id) LT2 on LT2.col_id=col_areas.col_id \
        WHERE status_code = 'active' \
        " + where + " \
        GROUP BY col_areas.col_id " + orderby + "", params, function(error, result) {
          if (error) {
            callback(error);
          } else {
            result.forEach(function(d) {
              if (d.sections) {
                d.sections = larkin.jsonifyPipes(d.sections, "integers");
              }
              d.units = larkin.jsonifyPipes(d.units, "integers");
              d.lith_types = larkin.jsonifyPipes(d.lith_types, "strings");
            });
            callback(null, data, result);
          }
      });
    }
  ], function(error, data, result) {
    if (error) {
      console.log(error);
      larkin.error(req, res, next, "An error was incurred");
    } else {
      if (req.query.format && api.acceptedFormats.geo[req.query.format]) {
        dbgeo.parse({
          "data": result,
          "geometryColumn": "wkt",
          "geometryType": "wkt",
          "outputFormat": larkin.getOutputFormat(req.query.format),
          "callback": function(error, output) {
            if (error) {
              larkin.error(req, res, next, "An error was incurred during conversion");
            } else {
              output.properties = data;
              if (larkin.getOutputFormat(req.query.format) === "geojson") {
                output = gp(output, 4);
              }
              if (api.acceptedFormats.bare[req.query.format]) {
                larkin.sendBare(output, res, next);
              } else {
                larkin.sendCompact(output, res, null, next);
              }
            }
          }
        });
      } else {
        larkin.sendData(result, res, (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json", next);
      }  
    }
  });
}
