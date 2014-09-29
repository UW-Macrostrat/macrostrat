var express = require("express"),
    mysql = require("mysql"),
    credentials = require("./credentials"),
    winston = require("winston"),
    async = require("async"),
    wellknown = require("wellknown"),
    larkin = require("../larkin"),
    dbgeo = require("dbgeo"),
    defs = require("./defs");

var api = express.Router();

api.use(function(req, res, next) {
  res.header("Access-Control-Allow-Origin", "*");
  res.header("Access-Control-Allow-Headers", "Origin, X-Requested-With, Content-Type, Accept");
  next();
});

api.acceptedFormats = {
  "standard": {
    "json": true,
    "csv": true
  },
  "geo": {
    "geojson": true,
    "topojson": true
  }
};

/*    /api    */
api.route("/")
  .get(function(req, res, next) {
    var routes = {};
    api.stack.filter(function(d) {
      if (d.route && d.route.path !== "*" && d.route.path !== null && d.route.path.length) {
        if (defs[d.route.path] && defs[d.route.path].visible) { 
          routes[d.route.path] = (defs[d.route.path] && defs[d.route.path].description) ? defs[d.route.path].description : "";
        }
      }
    });
    res.json({
      "success": {
        "description": "This is the root of the Macrostrat API",
        "routes": routes
      }
    });
  });

/*    /api/column?id=17    */
api.route("/column")
  .get(function(req, res, next) {
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
  });


/*    /api/columns?interval_name=Permian || /api/columns?age=250 || /api/columns?age_top=100&age_bottom=200    */
api.route("/columns")
  .get(function(req, res, next) {
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
        larkin.query("SELECT AsWKT(col_areas.col_area) AS wkt, col_areas.col_id, round(cols.col_area, 1) AS area, count(units.id) units, GROUP_CONCAT(units.id SEPARATOR '|') AS unit_id, sum(max_thick) max_thick, sum(min_thick) min_thick, sum(LT.cpm) lith_max_thick, sum(LT.cpl) lith_min_thick,  LT2.lts lith_types \
          FROM col_areas \
          JOIN cols ON cols.id = col_areas.col_id \
          JOIN units_sections ON units_sections.col_id = cols.id \
          JOIN units ON unit_id = units.id \
          JOIN lookup_unit_intervals ON lookup_unit_intervals.unit_id = units_sections.unit_id \
          JOIN (SELECT unit_id, round(sum(comp_prop*max_thick), 1) cpm, round(sum(comp_prop*min_thick), 1) cpl FROM unit_liths JOIN liths on lith_id=liths.id JOIN units on unit_id=units.id WHERE "+ lith_field +" like ? GROUP BY unit_id) LT ON LT.unit_id=units.id \
          JOIN (SELECT col_id, GROUP_CONCAT(distinct lith_type SEPARATOR '|') lts from liths JOIN unit_liths on lith_id=liths.id JOIN units_sections ON unit_liths.unit_id=units_sections.unit_id JOIN lookup_unit_intervals ON lookup_unit_intervals.unit_id=units_sections.unit_id WHERE "+ lith_field +" like ? AND FO_age > ? AND LO_age < ? GROUP BY col_id) LT2 on LT2.col_id=col_areas.col_id \
          WHERE FO_age > ? AND LO_age < ? AND status_code = 'active' \
          GROUP BY col_areas.col_id", [lith, lith, data.age_top, data.age_bottom, data.age_top, data.age_bottom], function(error, result) {
            if (error) {
              callback(error);
            } else {
              callback(null, data, result);
            }
        });
      }
    ], function(error, data, result) {
      if (error) {
        larkin.error(req, res, next, "An error was incurred");
      } else {
        dbgeo.parse({
          "data": result,
          "geometryColumn": "wkt",
          "geometryType": "wkt",
          "outputFormat": (api.acceptedFormats.geo[req.query.format]) ? req.query.format : "geojson",
          "callback": function(error, output) {
            if (error) {
              larkin.error(req, res, next, "An error was incurred during con");
            } else {
              output.properties = data;
              larkin.sendData(output, res, null, next);
            }
          }
        });
      }
    });
  });

/*     /api/unit    */
api.route("/unit")
  .get(function(req, res, next) {
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
  });


api.route("/units")
  .get(function(req, res, next) {
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

        var shortSQL = "units.id AS id,units_sections.section_id as section_id, units_sections.col_id as col_id, col_area, units.strat_name, mbr_name Mbr, fm_name Fm, gp_name Gp, sgp_name SGp, era, period, max_thick, min_thick, color, lith_type, count(distinct collection_no) pbdb";
              
        var longSQL = "units.id AS id,units_sections.section_id as section_id, units_sections.col_id as col_id, col_area, units.strat_name, mbr_name Mbr, fm_name Fm, gp_name Gp, sgp_name SGp, era, period, max_thick,min_thick, color, lith_class, lith_type, lith_short lith, environ_class, environ_type, environ, count(distinct collection_no) pbdb, FO_interval, FO_h, FO_age, b_age, LO_interval, LO_h, LO_age, t_age, position_bottom, notes"; 

        var sql = "SELECT " + ((req.query.response === "long") ? longSQL : shortSQL) + " FROM units \
              JOIN units_sections ON units_sections.unit_id=units.id \
              JOIN cols ON units_sections.col_id=cols.id \
              JOIN lookup_unit_liths ON lookup_unit_liths.unit_id=units.id \
              JOIN lookup_unit_intervals ON units.id=lookup_unit_intervals.unit_id \
              LEFT JOIN unit_strat_names ON unit_strat_names.unit_id=units.id \
              LEFT JOIN lookup_strat_names ON lookup_strat_names.strat_name_id=unit_strat_names.strat_name_id \
              " + ((req.query.response === "long") ? "LEFT JOIN unit_notes ON unit_notes.unit_id=units.id" : "") + " \
              LEFT JOIN pbdb_matches ON pbdb_matches.unit_id=units.id \
              WHERE status_code='active' AND FO_age > ? AND LO_age < ? and units.id IN (SELECT unit_liths.unit_id from unit_liths JOIN liths on lith_id=liths.id WHERE lith like " + lith_field + ") GROUP BY units.id";

        larkin.query(sql, [data.age_top, data.age_bottom], function(error, result) {
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
        larkin.sendData(result, res, "json", next);
      }
    });
  });


/*    /api/fossils?interval_name=Permian || /api/fossils?age=250 || /api/fossils?age_top=100&age_bottom=200    */
api.route("/fossils")
  .get(function(req, res, next) {
    if (Object.keys(req.query).length < 1) {
      return larkin.info(req, res, next);
    } else {
      async.waterfall([
        function(callback) {
          if (req.query.interval_name) {
            larkin.query("SELECT age_bottom,age_top,interval_name from intervals where interval_name = ? limit 1", [req.query.interval_name], function(error, result) {
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
            callback(null, {"interval_name": "Unknown", "age_bottom": req.query.age, "age_top": req.query.age});
          } else if (req.query.age_top && req.query.age_bottom) {
            callback(null, {"interval_name": "Unknown", "age_bottom": req.query.age_bottom, "age_top": req.query.age_top});
          } else {
            larkin.error(req, res, next, "Invalid parameters");
          }
        },
        function(data, callback) {
          larkin.query("SELECT pbdb_matches.collection_no, n_occs AS occ, \
            pbdb_matches.unit_id, AsWKT(pbdb_matches.coordinate) AS geometry \
            FROM pbdb_matches \
            JOIN units ON pbdb_matches.unit_id = units.id \
            JOIN units_sections ON units_sections.unit_id = units.id \
            JOIN cols ON cols.id = units_sections.col_id \
            JOIN intervals f ON f.id = FO \
            JOIN intervals l ON l.id = LO \
            JOIN pbdb.coll_matrix ON pbdb_matches.collection_no = pbdb.coll_matrix.collection_no \
            WHERE f.age_bottom > ? AND l.age_top < ? AND \
            status_code = 'active'", [data.age_top, data.age_bottom], function(error, result) {
              if (error) {
                callback(error);
              } else {
                callback(null, data, result);
              }
          });
        }
      ], function(error, data, results) {
        if (error) {
          larkin.error(req, res, next, "Something went wrong");
        } else {
          dbgeo.parse({
            "data": results,
            "outputFormat": (api.acceptedFormats.geo[req.query.format]) ? req.query.format : "geojson",
            "geometryColumn": "geometry",
            "geometryType": "wkt",
            "callback": function(error, result) {
              if (error) {
                larkin.error(req, res, next, "Something went wrong");
              } else {
                larkin.sendData(result, res, null, next);
              }
            }
          });
        }
      });
    }
      
  });

/*     /api/stats     */
api.route("/stats")
  .get(function(req, res, next) {
    if (Object.keys(req.query).length < 1) {
      return larkin.info(req, res, next);
    }

    var sql = "\
      SELECT project, COUNT(distinct units_sections.section_id) AS packages, COUNT(distinct unit_id) AS units, COUNT(distinct collection_no) AS pbdb_collections FROM units_sections \
          JOIN cols ON cols.id = col_id \
          JOIN projects ON projects.id = project_id \
          LEFT JOIN pbdb_matches USING (unit_id) \
          WHERE project IN ('North America','New Zealand','Caribbean','Deep Sea') and status_code='active' \
          GROUP BY project_id \
          ORDER BY field(project, 'North America','Caribbean','New Zealand','Deep Sea') ";

    var format = (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json";

    larkin.query(sql, [], null, true, res, format, next);
  });

/*     /api/lith_definitions     */
api.route("/lith_definitions")
  .get(function(req, res, next) {
    if (Object.keys(req.query).length < 1) {
      return larkin.info(req, res, next);
    }

    var sql = "SELECT id,lith,lith_type,lith_class,lith_color from liths";
        lith = "";

    if (req.query.all) {
      // do nothing
    } else if (req.query.lith_class) {
      sql += " WHERE lith_class = ?";  
      lith = req.query.lith_class;
    } else if (req.query.lith_type){
      sql += " WHERE lith_type = ?"; 
      lith = req.query.lith_type;
    }  else if (req.query.lith){
      sql += " WHERE lith = ? "; 
      lith = req.query.lith;
    }  else if (req.query.id){
      sql += " WHERE id = ? "; 
      lith = req.query.id;
    }

    var format = (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json";
    larkin.query(sql, [lith], null, true, res, format, next);
    
  });


/*     /api/lith_definitions     */
api.route("/lithatt_definitions")
  .get(function(req, res, next) {
    if (Object.keys(req.query).length < 1) {
      return larkin.info(req, res, next);
    }
    var sql = "SELECT id,lith_att,att_type from lith_atts";
        lithatt = "";

    if (req.query.all) {
      // do nothing
    } else if (req.query.att_type) {
      sql += " WHERE att_type = ?"; 
      lithatt = req.query.att_type;
    } else if (req.query.lith_att){
      sql += " WHERE lith_att = ?"; 
      lithatt = req.query.lith_att;
    } else if (req.query.id){
      sql += " WHERE id = ?"; 
      lithatt = req.query.id;
    }

    var format = (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json";
    larkin.query(sql, [lithatt], null, true, res, format, next);
  });

/*     /api/lith_definitions     */
api.route("/environ_definitions")
  .get(function(req, res, next) {
    if (Object.keys(req.query).length < 1) {
      return larkin.info(req, res, next);
    }
    var sql = "SELECT id,environ,environ_type,environ_class from environs";
        environ = "";
    if (req.query.all) {
      // do nothing
    } else if (req.query.environ_class) {
      sql += " WHERE environ_class= ?";
      environ=req.query.environ_class;
    } else if (req.query.environ_type){
      sql += " WHERE environ_type = ?";
      environ = req.query.environ_type;
    } else if (req.query.environ){
      sql += " WHERE environ = ?";
      environ = req.query.environ;
    } else if (req.query.id){
      sql += " WHERE id = ?";
      environ = req.query.id;
    }

    var format = (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json";
    larkin.query(sql, [environ], null, true, res, format, next);
  });

/*     /api/interval_definitions     */
api.route("/interval_definitions")
  .get(function(req, res, next) {
    if (Object.keys(req.query).length < 1) {
      return larkin.info(req, res, next);
    }

    var sql = "SELECT intervals.id, interval_name, age_top late_age, age_bottom early_age FROM intervals",
        params = [];

    if (req.query.all) {
      // do nothing
    } else if (req.query.timescale){
      sql += " JOIN timescales_intervals ON interval_id=intervals.id JOIN timescales ON timescale_id=timescales.id WHERE timescale = ?";
      params.push(req.query.timescale);
    } else if (req.query.id && isFinite(req.query.id)){
      sql += " WHERE id ="+req.query.id;
    }
    sql += " ORDER BY late_age ASC";
    var format = (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json";

    larkin.query(sql, params, null, true, res, format, next);
  });


/*    /api/strat_names    */
api.route("/strat_names")
  .get(function(req, res, next) {
    if (Object.keys(req.query).length < 1) {
      return larkin.info(req, res, next);
    }

    var filterString = "",
        params = [];

    if (req.query.all) {
      // do nothing
    } else if (req.query.id) {
      filterString += "strat_name_id = ?";
      params.push(req.query.id);
    } else if (req.query.name) {
      if (req.query.rank && req.query.rank.length <= 3 && req.query.rank.length >= 2 && /^[a-zA-Z]+$/.test(req.query.rank)){
        filterString += req.query.rank+"_name LIKE ?";
        params.push(req.query.name + "%");
      } else {
        filterString += "strat_name LIKE ?";
        params.push(req.query.name + "%");}
    } else if (req.query.rank) {
      filterString += "rank = ?";
      params.push(req.query.rank);
    }

    if (filterString.length > 1) {
      filterString = " WHERE "+filterString;
    }

    var sql = "SELECT strat_name name, rank, strat_name_id id, bed_name bed,bed_id,mbr_name mbr,mbr_id,fm_name fm,fm_id,gp_name gp,gp_id,sgp_name sgp,sgp_id,early_age,late_age FROM lookup_strat_names" + filterString;

    var format = (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json";

    larkin.query(sql, params, null, true, res, format, next);
  });

/*     /api/section_stats     */
api.route("/section_stats")
  .get(function(req, res, next) {
    if (Object.keys(req.query).length < 1) {
      return larkin.info(req, res, next);
    }
    if (req.query.age_model === "continuous") {
      var sql = "\
      SELECT project, units_sections.col_id col_id, units_sections.section_id section_id, count(distinct units.id) units, sum(max_thick) max_thick, sum(min_thick) min_thick, min(t1_age) t_age, max(t1_age) b_age \
      FROM units \
      JOIN units_sections ON units.id=unit_id \
      JOIN cols ON units_sections.col_id=cols.id \
      JOIN projects on project_id=projects.id \
      JOIN unit_boundaries ON units_sections.unit_id=unit_boundaries.unit_id \
      WHERE status_code='active' and units.id IN (SELECT distinct unit_id from unit_liths,liths where lith_id=liths.id and lith_class='sedimentary') and max_thick>0 and t1_age<=541 GROUP BY units_sections.section_id";
    } else if ("all" in req.query) {
      var sql = "\
        SELECT project,units_sections.col_id, units_sections.section_id, count(distinct units.id) units, sum(max_thick) max_thick, sum(min_thick) min_thick, min(l.age_top) t_age, max(f.age_bottom) b_age \
        FROM units \
        JOIN units_sections ON units.id=unit_id \
        JOIN cols ON units_sections.col_id=cols.id \
        JOIN projects on project_id=projects.id \
        JOIN intervals f ON f.id=FO \
        JOIN intervals l on l.id=LO \
        WHERE status_code='active' and units.id IN (SELECT distinct unit_id from unit_liths,liths where lith_id=liths.id and lith_class='sedimentary') and max_thick>0 and f.age_bottom<=541 GROUP BY units_sections.section_id";
    } else {
      return larkin.error(req, res, next, "Invalid parameters");
    }

    var format = (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json";

    larkin.query(sql, [], null, true, res, format, next);
  });


/*    /api/paleogeography?year=550   /api/paleogeography?interval=Permian */
api.route("/paleogeography")
  .get(function(req, res, next) {
    if (!req.query.age && !req.query.interval_name) {
      larkin.info(req, res, next);
    } else {
      async.waterfall([
        function(callback) {
          if (req.query.age) {
            callback(null, req.query.age);
          } else if (req.query.interval_name) {
            larkin.query("SELECT (age_bottom + age_top)/2 AS mid FROM intervals WHERE interval_name = ?", [req.query.interval_name], function(error, result) {
              if (error) {
                callback(error);
              } else {
                if (result.length === 1) {
                  callback(null, parseInt(result[0].mid));
                } else {
                  larkin.error(req, res, next, "interval not found");
                }
              }
            });
          }
        },
        function(year, callback) {
          larkin.queryPg("alice", "SELECT plateid, ST_AsGeoJSON(geom) AS geometry FROM merge.reconstructed_" + year + "_merged", [], function(error, result) {
            callback(null, result.rows);
          });
        }
      ], function(error, data) {
        if (error) {
          larkin.error(req, res, next, "Something went wrong");
        } else {
          dbgeo.parse({
            "data": data,
            "outputFormat": (api.acceptedFormats.geo[req.query.format]) ? req.query.format : "geojson",
            "callback": function(error, result) {
              if (error) {
                larkin.error(req, res, next, "Something went wrong");
              } else {
                larkin.sendData(result, res, null, next);
              }
            }
          });
        }
      });
    }
  });
/*
  TODO:
    I think instead of geo=true, we should use format=geojson or format=topojson
*/
api.route("/geologic_units")
  .get(function(req, res, next) {
    if (Object.keys(req.query).length < 1) {
      larkin.info(req, res, next);
    } else {
      var geo = (req.query.geo && req.query.geo === "true") ? true : false,
          types = (req.query.type) ? req.query.type.split(",") : ["gmna", "gmus", "column"];

      async.parallel({
        gmus: function(callback) {
          if (types.indexOf("gmna") > -1) {
            larkin.queryPg("earthbase", "SELECT gid, state, a.rocktype1, a.rocktype2, b.rocktype3, unit_name, b.unit_age, unitdesc, strat_unit, unit_com" + ((geo) ? ", ST_AsGeoJSON(a.the_geom) AS geometry" : "") + " FROM gmus.geologic_units a JOIN gmus.units b ON a.unit_link = b.unit_link WHERE ST_Contains(the_geom, ST_GeomFromText($1, 4326))", ["POINT(" + req.query.lng + " " + req.query.lat + ")"], function(error, result) {
              if (error) {
                callback(error);
              } else {
                if (geo) {
                  result.rows[0].geometry = JSON.parse(result.rows[0].geometry);
                }
                callback(null, result.rows[0]);
              }
            });
          } else {
            callback(null);
          } 
        },

        gmna: function(callback) {
          if (types.indexOf("gmus") > -1) {
            larkin.queryPg("earthbase", "SELECT objectid, unit_abbre, rocktype, lithology, min_age, max_age, min_max_re, unit_uncer, age_uncert" + ((geo) ? ", ST_AsGeoJSON(the_geom) AS geometry" : "") + " FROM gmna.geologic_units WHERE ST_Contains(the_geom, ST_GeomFromText($1, 4326))", ["POINT(" + req.query.lng + " " + req.query.lat + ")"], function(error, result) {
              if (error) {
                callback(error);
              } else {
                if (geo) {
                  result.rows[0].geometry = JSON.parse(result.rows[0].geometry);
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
                  col[0].geometry = wellknown(column.wkt);
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
  });

api.route("/geologic_units/map")
  .get(function(req, res, next) {
    if (Object.keys(req.query).length < 1) {
      return larkin.info(req, res, next);
    }
    if (req.query.type === "gmus") {
      larkin.queryPg("earthbase", "SELECT a.gid, a.unit_age, a.rocktype1, a.rocktype2, b.cmin_age, ST_AsGeoJSON(a.the_geom) AS geometry from gmus.geologic_units a JOIN gmus.age b ON a.unit_link = b.unit_link WHERE b.cmin_age = $1", [req.query.interval_name], function(error, result) {
        dbgeo.parse({
          "data": result.rows,
          "outputFormat": (api.acceptedFormats.geo[req.query.format]) ? req.query.format : "geojson",
          "callback": function(error, result) {
            if (error) {
              larkin.error(req, res, next, error);
            } else {
              larkin.sendData(result, res, null, next);
            }
          }
        });
      });
    } else if (req.query.type === "gmna") {
      larkin.queryPg("earthbase", "SELECT a.gid, a.rocktype, ST_AsGeoJSON(the_geom) AS geometry, b.interval_name from gmna.geologic_units a JOIN gmna.intervals_old b ON a.eb_interval_id = b.interval_id where b.interval_name = $1", [req.query.interval_name], function(error, result) {
        dbgeo.parse({
          "data": result.rows,
          "outputFormat": (api.acceptedFormats.geo[req.query.format]) ? req.query.format : "geojson",
          "callback": function(error, result) {
            if (error) {
              larkin.error(req, res, next, error);
            } else {
              larkin.sendData(result, res, null, next);
            }
          }
        });
      });
    } else {
      larkin.error(req, res, next, "Invalid parameters");
    }
      
  });

api.route("/mobile/point")
  .get(function(req, res, next) {
    if (req.query.lat && req.query.lng) {
      async.parallel([
        // Query GMUS for unit name
        function(callback) {
          larkin.queryPg("earthbase", "SELECT gid AS unit_id, unit_name FROM gmus.geologic_units a JOIN gmus.units b ON a.unit_link = b.unit_link WHERE ST_Contains(the_geom, ST_GeomFromText($1, 4326))", ["POINT(" + req.query.lng + " " + req.query.lat + ")"], function(error, result) {
            if (error) {
              callback(error);
            } else {
              callback(null, result.rows[0]);
            }
          });
        },

        // Query Macrostrat for polygon
        function(callback) {
          larkin.query("SELECT col_id, AsWKT(col_areas.col_area) AS col_poly FROM col_areas JOIN cols on col_id = cols.id WHERE ST_CONTAINS(col_areas.col_area, ST_GEOMFROMTEXT('POINT(? ?)')) and status_code='active'", [parseFloat(req.query.lng), parseFloat(req.query.lat)], function(error, result) {
              if (error) {
                callback(error);
              } else {
                if (result.length < 1) {
                  callback("No columns found");
                } else if (result.length > 1) {
                  callback("More than 1 column found");
                } else {
                  callback(null, result[0]);
                }
              }
            });
        }
      ], function(error, results) {
        if (error) {
          larkin.error(req, res, next, error);
        } else {
          var result = {
            "unit_id": results[0].unit_id,
            "unit_name": results[0].unit_name,
            "col_id": results[1].col_id,
            "col_poly": (req.query.geo_format === "wkt") ? wellknown.stringify(wellknown(results[1].col_poly), 6) : wellknown(results[1].col_poly, 6)
          };
          larkin.sendData(result, res, null, next);
        }
      });
        
    } else {
      larkin.info(req, res, next);
    }
      
  });

api.route("/mobile/point_details")
  .get(function(req, res, next) {
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
              larkin.query("SELECT col_id FROM col_areas JOIN cols on col_id=cols.id WHERE ST_CONTAINS(col_areas.col_area,ST_GEOMFROMTEXT('POINT(? ?)')) and status_code='active'", [parseFloat(req.query.lng), parseFloat(req.query.lat)], function(error, result) {
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
                  
              var sql = "SELECT units.id AS id, units.strat_name, period, max_thick, min_thick, color, count(distinct collection_no) pbdb, lith_short AS lith FROM units \
                  JOIN units_sections ON units_sections.unit_id = units.id \
                  JOIN lookup_unit_liths ON lookup_unit_liths.unit_id=units.id \
                  JOIN lookup_unit_intervals ON units.id=lookup_unit_intervals.unit_id \
                  LEFT JOIN unit_strat_names ON unit_strat_names.unit_id=units.id \
                  LEFT JOIN lookup_strat_names ON lookup_strat_names.strat_name_id=unit_strat_names.strat_name_id \
                  LEFT JOIN pbdb_matches ON pbdb_matches.unit_id=units.id \
                  WHERE units_sections.col_id = ? \
                  GROUP BY units.id ORDER BY t_age ASC";

              larkin.query(sql, [column.col_id], function(error, result) {
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
              col[0].units = result;
              callback(null, col[0]);
            }
          });
        }
      }, function(error, results) {
        if (error) {
          larkin.error(req, res, next, "Something went wrong");
        } else {
          larkin.sendData(results, res, "json", next);
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
              larkin.query("SELECT id, col_name FROM cols WHERE id = ?", [req.query.col_id], function(error, result) {
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

            function(column_info, callbackB) {
              larkin.query("SELECT units.id AS id, units.strat_name, period, max_thick, min_thick, color, count(distinct collection_no) AS pbdb, lith_short AS lith FROM units JOIN units_sections ON units_sections.unit_id = units.id JOIN lookup_unit_liths ON lookup_unit_liths.unit_id=units.id JOIN lookup_unit_intervals ON units.id=lookup_unit_intervals.unit_id LEFT JOIN pbdb_matches ON pbdb_matches.unit_id = units.id WHERE units_sections.col_id = ? GROUP BY units.id ORDER BY t_age ASC", [req.query.col_id], function(error, result) {
                if (error) {
                  callbackB(error);
                } else {
                  callbackB(null, column_info, result);
                }
              });
            }
          ],
          // after the two queries are executed, send the result
          function(err, column_info, result) {
            if (err) {
              callback(err);
            } else {
              var col = [column_info];
              col[0].units = result;
              callback(null, col[0]);
            }
          });
        }
      }, function(error, results) {
        if (error) {
          larkin.error(req, res, next, "Something went wrong");
        } else {
          larkin.sendData(results, res, "json", next);
        }
      });
    } else {
      larkin.info(req, res, next);
    }
  });

api.route("/mobile/fossil_collections")
  .get(function(req, res, next) {
    if (req.query.unit_id) {
      larkin.query("SELECT DISTINCT collection_no AS cltn_no FROM pbdb_matches WHERE unit_id = ?", [req.query.unit_id], function(error, result) {
        if (error) {
          larkin.error(req, res, next, error);
        } else {
          var data = {
            "pbdb_collections": result.map(function(n) { return n.cltn_no; })
          };
          larkin.sendData(data, res, "json", next);
        }
      });
    } else {
      larkin.info(req, res, next);
    }
  });

api.route("/editing/map")
  .get(function(req, res, next) {
    if (req.query.id) {
      // return just that polygons and the ones that touch it
      larkin.queryPg("macrostrat_editing", "SELECT b.col_id, ST_AsGeoJSON(b.geom) AS geometry FROM col_areas AS a JOIN col_areas AS b ON ST_Intersects(st_snaptogrid(a.geom,0.001), st_snaptogrid(b.geom,0.001)) WHERE a.col_id = $1 OR b.col_id = $1 GROUP BY b.col_id, b.geom ORDER BY b.col_id ASC;", [req.query.id], function(error, result) {
        dbgeo.parse({
          "data":result.rows,
          "outputFormat": "geojson",
          "callback": function(error, result) {
            if (error) {
              larkin.error(req, res, next, error);
            } else {
              larkin.sendData(result, res, null, next);
            }
          }
        });
      });
    } else {
      // return all polygons
      larkin.queryPg("macrostrat_editing", "SELECT col_id, ST_AsGeoJSON(geom) as geometry FROM col_areas", [], function(error, result) {
        dbgeo.parse({
          "data":result.rows,
          "outputFormat": "geojson",
          "callback": function(error, result) {
            if (error) {
              larkin.error(req, res, next, error);
            } else {
              larkin.sendData(result, res, null, next);
            }
          }
        });
      });
    }
  });

api.route("/editing/map/update")
  .post(function(req, res, next) {
    if (req.body.layer) {
      req.body.layer = JSON.parse(req.body.layer);
      async.each(req.body.layer.features, function(feature, callback) {
        larkin.queryPg("macrostrat_editing", "SELECT ST_isValid(ST_GeomFromText( '" + wellknown.stringify(feature.geometry) + "')) AS isvalid", [], function(error, result) {
          if (result.rows[0].isvalid) {
            callback();
          } else {
            callback("invalid");
          }
        });

      }, function(error) {
        if (error) {
          larkin.error(req, res, next, error);
        } else {
          async.each(req.body.layer.features, function(feature, callback) {
            larkin.queryPg("macrostrat_editing", "UPDATE col_areas SET geom = ST_GeomFromText('" + wellknown.stringify(feature.geometry) + "') WHERE col_id = $1", [feature.properties.col_id], function(error, result) {
              callback();
            });
          }, function(error) {
            larkin.sendData([{"update": "success"}], res, null, next);
          });
        }
      });

    } else {
      larkin.error(req, res, next, "A layer is required");
    }
  });

api.route("/editing/units")
  .get(function(req, res, next) {

  });

api.route("/editing/units/update")
  .post(function(req, res, next) {

  });

/* Handle errors and unknown pages */
api.route("*")
  .get(function(req, res, next) {
    var err = new Error();
    err.status = 404;
    next(err);
  });

api.use(function(err, req, res, next) {
  if(err.status !== 404) {
    return next();
  } else if (err.status === 404) {
    larkin.error(req, res, next, "404: Page not found", 404);
  } else {
    larkin.error(req, res, next, "500: Internal Server Error", 500);
  }
});

// Export the module
module.exports = api;
