var express = require("express"),
    mysql = require("mysql"),
    credentials = require("./credentials"),
    winston = require("winston"),
    async = require("async"),
    wellknown = require("wellknown"),
    larkin = require("../larkin"),
    dbgeo = require("dbgeo");


var api = express.Router();

api.use(function(req, res, next) {
  res.header("Access-Control-Allow-Origin", "*");
  res.header("Access-Control-Allow-Headers", "Origin, X-Requested-With, Content-Type, Accept");
  next();
});

api.acceptedFormats = {
  "json": true,
  "geojson": true,
  "topojson": true,
  "csv": true
};

/*    /api    */
api.route("/")
  .get(function(req, res, next) {
    var routes = [];
    api.stack.map(function(d) { 
      if (d.route && d.route.path != "*" && d.route.path !== null && d.route.path.length) {
        routes.push(d.route.path);
      } 
    });
    res.json({
      "success": {
        "about": "This is the root of the Macrostrat API",
        "routes": api.stack.filter(function(d) { 
          if (d.route && d.route.path != "*" && d.route.path !== null && d.route.path.length) {
            return d.route.path;
          } 
        })
        .map(function(d) {
          return d.route.path;
        })
      }
    });
  });

/*    /api/columns?id=17    */
api.route("/columns")
  .get(function(req, res, next) {
    if (isFinite(req.query.id) || isFinite(req.query.lat) && isFinite(req.query.lng)) {
      async.waterfall([
        function(callback) {
          if (req.query.lat){
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
          larkin.query("SELECT id, col_name FROM cols WHERE id = ?", [column_id], function(error, result) {
            if (error) {
              callback(error);
            } else {
              if (result.length === 0) {
                larkin.error(res, next, "No results found.");
              } else {
                callback(null, column_id, result[0]);
              }
            }
          });
        },

        function(column_id, column_info, callback) {
          var shortSQL = "units.id AS unit_id,mbr_name Mbr, fm_name Fm, gp_name Gp, sgp_name SGp, GROUP_CONCAT(lith,'-',comp_prop,'' SEPARATOR ',') AS liths ",
              longSQL = "units.id AS unit_id, mbr_name Mbr, fm_name Fm, gp_name Gp, sgp_name SGp, units.strat_name, units_sections.section_id, max_thick, min_thick, f.id AS F_id, f.interval_name AS F_int, f.age_bottom AS F_agebot, f.age_top AS F_agetop, FO_h,l.id AS L_id, l.interval_name AS L_int, l.age_bottom AS L_agebot, l.age_top AS L_agetop, LO_h, position_bottom, u1.unit_id AS t_uid1,u1.unit_id_2 AS t_uid2,u1.t1 AS t_int_id,u1.t1_prop AS t_prop, u1.t1_age AS t_age, u2.unit_id_2 AS b_uid2, u2.unit_id AS b_uid1, u2.t1 AS b_int_id, u2.t1_prop AS b_prop, u2.t1_age AS b_age, color, GROUP_CONCAT(lith,'-',comp_prop,'' SEPARATOR ',') AS liths ";

          larkin.query("SELECT " + ((req.query.response === "short") ? shortSQL : longSQL) + " \
            FROM units\
            JOIN units_sections ON units_sections.unit_id = units.id\
            JOIN unit_liths ON unit_liths.unit_id = units.id \
            JOIN liths ON lith_id = liths.id \
            JOIN intervals f ON f.id = FO \
            JOIN intervals l ON l.id = LO \
            LEFT JOIN unit_strat_names ON unit_strat_names.unit_id=units.id \
            LEFT JOIN strat_name_lookup ON strat_name_lookup.strat_name_id=unit_strat_names.strat_name_id \
            LEFT JOIN unit_boundaries u1 ON u1.unit_id = units.id \
            LEFT JOIN unit_boundaries u2 ON u2.unit_id_2 = units.id \
            WHERE units_sections.col_id = ? \
            GROUP BY units.id ORDER BY u2.t1_age ASC", [column_id], function(error, result) {
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
          larkin.error(res, next, err);
        } else {
          var column = [column_info];
          column[0].units = result;
          var format = "json";
          larkin.sendData(column, res, format, next);
        }
      });

    } else {
      larkin.error(res, next, "Please provide a parameter id corresponding to column id (api/columns?id=17) or a latitude and longitude (api/columns?lat=50&lng=-80");
    }
  });

/*    /api/fossils?interval_name=Permian || /api/fossils?age=250 || /api/fossils?age_top=100&age_bottom=200    */
api.route("/fossils")
  .get(function(req, res, next) {
    async.waterfall([
      function(callback) {
        if (req.query.interval_name) {
          larkin.query("SELECT age_bottom,age_top,interval_name from intervals where interval_name = ? limit 1", [req.query.interval_name], function(error, result) {
            if (error) {
              callback(error);
            } else {
              if (result.length === 0) {
                larkin.error(res, next, "No results found");
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
          larkin.error(res, next, "Please provide an interval_name, age, or age_top & age_bottom. Examples: /api/fossils?interval_name=Permian  /api/fossils?age=271 <br> /api/fossils?age_top=200&age_bottom=250");
        }
      },
      function(data, callback) {
        larkin.query("SELECT COUNT(pbdb.occurrences.occurrence_no) AS occ, pbdb_matches.collection_no,\
          pbdb_matches.unit_id, AsWKT(pbdb_matches.coordinate) AS geometry \
          FROM pbdb_matches \
          JOIN units ON pbdb_matches.unit_id = units.id \
          JOIN units_sections ON units_sections.unit_id = units.id \
          JOIN cols ON cols.id = units_sections.col_id \
          JOIN intervals f ON f.id = FO \
          JOIN intervals l ON l.id = LO \
          JOIN pbdb.occurrences ON pbdb_matches.collection_no = pbdb.occurrences.collection_no \
          WHERE f.age_bottom > ? AND l.age_top < ? AND \
          status_code = 'active' AND project_id IN (1,7) GROUP BY collection_no", [data.age_top, data.age_bottom], function(error, result) {
            if (error) {
              callback(error);
            } else {
              callback(null, data, result);
            }
        });
      }
    ], function(error, data, results) {
      if (error) {
        larkin.error(res, next, error);
      } else {
        dbgeo.parse({
          "data": results,
          "outputFormat": (api.acceptedFormats[req.query.format]) ? req.query.format : "geojson",
          "geometryColumn": "geometry",
          "geometryType": "wkt",
          "callback": function(error, result) {
            if (error) {
              larkin.error(res, next, error);
            } else {
              larkin.sendData(result, res, null, next);
            }
          }
        });
      }
    });
  });

/*    /api/strats?interval_name=Permian || /api/strats?age=250 || /api/strats?age_top=100&age_bottom=200    */
api.route("/strats")
  .get(function(req, res, next) {
    async.waterfall([
      function(callback) {
        if (req.query.interval_name) {
          larkin.query("SELECT age_bottom,age_top,interval_name from intervals where interval_name = ? LIMIT 1", [req.query.interval_name], function(error, result) {
            if (error) {
              callback(error);
            } else {
              if (result.length === 0) {
                larkin.error(res, next, "No results found");
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
          larkin.error(res, next, "You must specify an age argument to get a result. This can be of form: ?interval_name=string or ?age=234 or ?age_bottom=234&age_top=230 NB: this version does NOT use continuous time age model for units. Therefore an age may return units that are not of that exact age but in a bin spanning that age. Output is geoJSON.  Unit lithologies for time interval in each column are given.  The order of lith,lith_type,p is the same in each group and corresponds to the unique lithologies in that column for the requested age on a per-unit basis (i.e., thickness is ignored).")
        }
      },
      function(data, callback) {
        larkin.query("SELECT col_areas.col_id, cols.col_area AS area, AsWKT(col_areas.col_area) AS wkt, \
          GROUP_CONCAT(units.id SEPARATOR ',') AS units \
          FROM col_areas \
          JOIN cols ON cols.id = col_areas.col_id \
          JOIN units_sections ON units_sections.col_id = cols.id \
          JOIN units ON unit_id = units.id \
          JOIN intervals f ON f.id = FO \
          JOIN intervals l ON l.id = LO \
          WHERE f.age_bottom > ? AND l.age_top < ? \
          AND status_code = 'active' AND project_id IN (1,7) GROUP BY col_areas.col_id", [data.age_top, data.age_bottom], function(error, result) {
            if (error) {
              callback(error);
            } else {
              callback(null, data, result);
            }
          });
      }
    ], function(error, data, result) {
      if (error) {
        larkin.error(res, next, error);
      } else {
        dbgeo.parse({
          "data": result,
          "geometryColumn": "wkt",
          "geometryType": "wkt",
          "outputFormat": (api.acceptedFormats[req.query.format]) ? req.query.format : "geojson",
          "callback": function(error, output) {
            if (error) {
              larkin.error(res, next, error);
            } else {
              output.properties = data;
              larkin.sendData(output, res, null, next);
            }
          } 
        });
      }
    });
  });

/*     /api/stats     */
api.route("/stats")
  .get(function(req, res, next) {
    var sql = "\
      SELECT project, COUNT(distinct section_id) AS packages, COUNT(distinct units.id) AS units, COUNT(distinct collection_no) AS pbdb_collections FROM units \
          INNER JOIN cols ON cols.id = col_id \
          INNER JOIN projects ON projects.id = project_id \
          LEFT OUTER JOIN pbdb_matches ON unit_id = units.id \
            WHERE project IN ('North America','New Zealand','Caribbean','Deep Sea') and status_code='active' \
          GROUP BY project_id \
          ORDER BY field(project, 'North America','Caribbean','New Zealand','Deep Sea') ";

    var format = (api.acceptedFormats[req.query.format]) ? req.query.format : "json";

    larkin.query(sql, [], null, true, res, format, next);
  });

/*     /api/lith_definitions     */
api.route("/lith_definitions")
  .get(function(req, res, next) {
    var sql = "SELECT id,lith,lith_type,lith_class,lith_color from liths";

    if (req.query.lith_class) {
      sql += " WHERE lith_class='"+ req.query.lith_class +"'";
    } else if (req.query.lith_type){
      sql += " WHERE lith_type='"+ req.query.lith_type +"'";
    }  else if (req.query.lith){
      sql += " WHERE lith='"+ req.query.lith +"'";
    }

    var format = (api.acceptedFormats[req.query.format]) ? req.query.format : "json";
    larkin.query(sql, [], null, true, res, format, next);
  });

/*     /api/lith_definitions     */
api.route("/lithatt_definitions")
  .get(function(req, res, next) {
    var sql = "SELECT id,lith_att,att_type from lith_atts";
    var format = (api.acceptedFormats[req.query.format]) ? req.query.format : "json";

    if (req.query.att_type) {
      sql += " WHERE att_type='"+ req.query.att_type +"'";
    } else if (req.query.lith_att){
      sql += " WHERE lith_att='"+ req.query.lith_att +"'";
    }

    larkin.query(sql, [], null, true, res, format, next);
  });

/*     /api/lith_definitions     */
api.route("/environ_definitions")
  .get(function(req, res, next) {
    var sql = "SELECT id,environ,environ_type,environ_class from environs";

    if (req.query.environ_class) {
      sql += " WHERE environ_class='"+ req.query.environ_class +"'";
    } else if (req.query.environ_type){
      sql += " WHERE environ_type='"+ req.query.environ_type +"'";
    } else if (req.query.environ){
      sql += " WHERE environ='"+ req.query.environ +"'";
    }
    
    var format = (api.acceptedFormats[req.query.format]) ? req.query.format : "json";
    larkin.query(sql, [], null, true, res, format, next);
  });

/*     /api/interval_definitions     */
api.route("/interval_definitions")
  .get(function(req, res, next) {
    var sql = "SELECT intervals.id, interval_name, age_top late_age, age_bottom early_age FROM intervals",
        params = [];
    if (req.query.timescale){
      sql += " JOIN timescales_intervals ON interval_id=intervals.id JOIN timescales ON timescale_id=timescales.id WHERE timescale = ?";
      params.push(req.query.timescale);
    }
    sql += " ORDER BY late_age ASC";
    var format = (api.acceptedFormats[req.query.format]) ? req.query.format : "json";

    larkin.query(sql, params, null, true, res, format, next);
  });

/*    /api/strat_names    */
api.route("/strat_names")
  .get(function(req, res, next) {
    var filterString = "",
        params = [];

    if (req.query.id) {
      filterString += "AND sn.id = ?";
      params.push(req.query.id);
    } 
    if (req.query.name) {
      filterString += "AND sn.strat_name LIKE ? ";
      params.push(req.query.name + "%");
    } 
    if (req.query.parent_name) {
      filterString += "AND sn2.strat_name LIKE ? ";
      params.push(req.query.parent_name + "%");
    }
    if (req.query.rank) {
      filterString += "AND sn.rank = ? ";
      params.push(req.query.rank);
    }
    if (req.query.parent_rank) {
      filterString += "AND sn2.rank = ? ";
      params.push(req.query.parent_rank);
    }

    var sql = "\
      SELECT sn.id as id, sn.strat_name, sn.rank, st.this_name AS parent_id, sn2.strat_name AS parent_name, sn2.rank AS parent_rank \
          FROM unit_strat_names usn \
            JOIN strat_names AS sn ON usn.strat_name_id = sn.id \
            JOIN units AS u ON u.id = sn.id \
            LEFT JOIN strat_tree AS st ON st.that_name = sn.id \
            LEFT JOIN strat_names AS sn2 ON st.this_name = sn2.id \
            JOIN cols AS c ON u.col_id = c.id \
            LEFT JOIN strat_tree AS st2 ON st2.this_name = sn.id \
                WHERE project_id = 1 AND status_code LIKE 'active' " + filterString + " \
         GROUP BY sn.id \
         ORDER BY sn.strat_name";

    var format = (api.acceptedFormats[req.query.format]) ? req.query.format : "json";

    larkin.query(sql, params, null, true, res, format, next);
  });


/*     /api/section_stats     */
api.route("/section_stats")
  .get(function(req, res, next) {
    if (req.query.age_model === "continuous") {
      var sql = "\
      SELECT project, units_sections.col_id col_id, units_sections.section_id section_id, count(distinct units.id) units, sum(max_thick) max_thick, sum(min_thick) min_thick, min(t1_age) t_age, max(t1_age) b_age \
      FROM units \
      JOIN units_sections ON units.id=unit_id \
      JOIN cols ON units_sections.col_id=cols.id \
      JOIN projects on project_id=projects.id \
      JOIN unit_boundaries ON units_sections.unit_id=unit_boundaries.unit_id \
      WHERE status_code='active' and units.id IN (SELECT distinct unit_id from unit_liths,liths where lith_id=liths.id and lith_class='sedimentary') and max_thick>0 and t1_age<=541 GROUP BY units_sections.section_id";
    } else {
      var sql = "\
        SELECT project,units_sections.col_id, units_sections.section_id, count(distinct units.id) units, sum(max_thick) max_thick, sum(min_thick) min_thick, min(l.age_top) t_age, max(f.age_bottom) b_age \
        FROM units \
        JOIN units_sections ON units.id=unit_id \
        JOIN cols ON units_sections.col_id=cols.id \
        JOIN projects on project_id=projects.id \
        JOIN intervals f ON f.id=FO \
        JOIN intervals l on l.id=LO \
        WHERE status_code='active' and units.id IN (SELECT distinct unit_id from unit_liths,liths where lith_id=liths.id and lith_class='sedimentary') and max_thick>0 and f.age_bottom<=541 GROUP BY units_sections.section_id";
    }

    var format = (api.acceptedFormats[req.query.format]) ? req.query.format : "json";

    larkin.query(sql, [], null, true, res, format, next);
  });


/*    /api/paleogeography?year=550   /api/paleogeography?interval=Permian */
api.route("/paleogeography")
  .get(function(req, res, next) {
    if (!req.query.year && !req.query.interval) {
      larkin.error(res, next, "Please specify a year between 0 and 550 MA or a named interval");
    } else {
      async.waterfall([
        function(callback) {
          if (req.query.year) {
            callback(null, req.query.year);
          } else if (req.query.interval) {
            larkin.query("SELECT (age_bottom + age_top)/2 AS mid FROM intervals WHERE interval_name = ?", [req.query.interval], function(error, result) {
              if (error) {
                callback(error);
              } else {
                if (result.length === 1) {
                  callback(null, parseInt(result[0].mid));
                } else {
                  larkin.error(res, next, "interval not found");
                }
              }
            });
          }
        },
        function(year, callback) {
          larkin.queryPg("alice", "SELECT plateid, ST_AsGeoJSON(geom) AS geometry FROM merge.reconstructed_" + year + "_merged", [], function(result) {
            callback(null, result.rows);
          });
        }
      ], function(error, data) {
        if (error) {
          larkin.error(res, next, error);
        } else {
          dbgeo.parse({
            "data": data,
            "outputFormat": (req.query.format && req.query.format === "geojson" || req.query.format === "topojson") ? req.query.format : "geojson",
            "callback": function(error, result) {
              if (error) {
                larkin.error(res, next, error);
              }
              larkin.sendData(result, res, null, next);
            }
          });
        }
      });
    }
  });

api.route("/editing")
  .get(function(req, res, next) {
    if (req.query.id) {
      // return just that polygons and the ones that touch it
    //  larkin.queryPg("macrostrat_editing", "SELECT col_id, ST_AsGeoJSON(geom) AS geometry FROM (SELECT col_id, geom FROM col_areas) q WHERE ST_Touches((SELECT geom FROM col_areas WHERE col_id = $1), geom) OR col_id = $1", [req.query.id], function(result) {
      larkin.queryPg("macrostrat_editing", "SELECT b.col_id, ST_AsGeoJSON(b.geom) AS geometry FROM col_areas AS a JOIN col_areas AS b ON ST_Intersects(st_snaptogrid(a.geom,0.001), st_snaptogrid(b.geom,0.001)) WHERE a.col_id = $1 OR b.col_id = $1 GROUP BY b.col_id, b.geom ORDER BY b.col_id ASC;", [req.query.id], function(result) {
        dbgeo.parse({
          "data":result.rows,
          "outputFormat": "geojson",
          "callback": function(error, result) {
            if (error) {
              larkin.error(res, next, error);
            } else {
              larkin.sendData(result, res, null, next);
            }
          }
        });
      });
    } else {
      // return all polygons
      larkin.queryPg("macrostrat_editing", "SELECT col_id, ST_AsGeoJSON(geom) as geometry FROM col_areas", [], function(result) {
        dbgeo.parse({
          "data":result.rows,
          "outputFormat": "geojson",
          "callback": function(error, result) {
            if (error) {
              larkin.error(res, next, error);
            } else {
              larkin.sendData(result, res, null, next);
            }
          }
        });
      });
    }
  });

api.route("/editing/update")
  .post(function(req, res, next) {
    if (req.body.layer) {
      req.body.layer = JSON.parse(req.body.layer);
      async.each(req.body.layer.features, function(feature, callback) {
      //  larkin.queryPg("macrostrat_editing", "SELECT ST_isValid(st_geomfromgeojson( '" + JSON.stringify(feature.geometry) + "')) AS isvalid", [], function(result) {
        larkin.queryPg("macrostrat_editing", "SELECT ST_isValid(ST_GeomFromText( '" + wellknown.stringify(feature.geometry) + "')) AS isvalid", [], function(result) {
          if (result.rows[0].isvalid) {
            callback();
          } else {
            callback("invalid");
          }
        });
        
      }, function(error) {
        if (error) {
          larkin.error(res, next, error);
        } else {
          async.each(req.body.layer.features, function(feature, callback) {
            //larkin.queryPg("macrostrat_editing", "UPDATE col_areas SET geom = st_geomfromgeojson('" + JSON.stringify(feature.geometry) + "') WHERE col_id = $1", [feature.properties.col_id], function(result) {
            larkin.queryPg("macrostrat_editing", "UPDATE col_areas SET geom = ST_GeomFromText('" + wellknown.stringify(feature.geometry) + "') WHERE col_id = $1", [feature.properties.col_id], function(result) {
              callback();
            });
          }, function(error) {
            larkin.sendData([{"update": "success"}], res, null, next);
          });
        }
      });

    } else {
      larkin.error(res, next, "A layer is required");
    }
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
    larkin.error(res, next, "404: Page not found", null, 404);
  } else {
    larkin.error(res, next, "500: Internal Server Error", null, 500);
  }
});

// Export the module
module.exports = api;
