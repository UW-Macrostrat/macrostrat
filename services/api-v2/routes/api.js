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
    var routes = [];
    api.stack.filter(function(d) {
      if (d.route && d.route.path !== "*" && d.route.path !== null && d.route.path.length) {
        routes.push(d.route.path);
      }
    });
    //console.log(api.stack);
    res.json({
      "success": {
        "about": "This is the root of the Macrostrat API",
        "routes": routes
      }
    });
  });

/*    /api/column?id=17    */
api.route("/column")
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
          var shortSQL = "units.id AS id,units.strat_name, mbr_name Mbr, fm_name Fm, gp_name Gp, sgp_name SGp, era, period, max_thick,min_thick, color, lith_type liths, count(distinct collection_no) pbdb";
              longSQL = "units.id AS id,units_sections.section_id, units.strat_name, mbr_name Mbr, fm_name Fm, gp_name Gp, sgp_name SGp, era, period, max_thick,min_thick, color, lith_short liths, GROUP_CONCAT(collection_no SEPARATOR '|') pbdb, FO_interval, FO_h, FO_age, b_age, LO_interval, LO_h, LO_age, t_age, position_bottom ";

          larkin.query("SELECT " + ((req.query.response === "long") ? longSQL : shortSQL) + " \
            FROM UNITS \
            JOIN units_sections ON units_sections.unit_id = units.id \
            JOIN lookup_unit_liths ON lookup_unit_liths.unit_id=units.id \
            JOIN lookup_unit_intervals ON units.id=lookup_unit_intervals.unit_id \
            LEFT JOIN unit_strat_names ON unit_strat_names.unit_id=units.id \
            LEFT JOIN lookup_strat_names ON lookup_strat_names.strat_name_id=unit_strat_names.strat_name_id \
            LEFT JOIN pbdb_matches ON pbdb_matches.unit_id=units.id \
            WHERE units_sections.col_id = ? \
            GROUP BY units.id ORDER BY t_age ASC", [column_id], function(error, result) {
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
          larkin.log("error", error);
          larkin.error(res, next);
        } else {
          var column = [column_info];
          column[0].units = result;
          var format = "json";
          larkin.sendData(column, res, format, next);
        }
      });

    } else {
      larkin.error(res, next, "Please provide a column id or a latitude and longitude.", {
        "parameters": {
          "id": "Get a column by id",
          "lat": "A valid latitude",
          "lng": "A valid longitude",
          "response": "Can be 'short' or 'long'"
        },
        "output_formats": "json",
        "examples": ["api/columns?id=17", "api/columns?lat=50&lng=-80"]
      });
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
          larkin.error(res, next, "Please provide an interval_name, age, or age_top & age_bottom.", {
            "parameters": {
              "interval_name": "The name of a time interval",
              "age": "A valid age",
              "age_top": "A valid age - must be used with age_bottom and be less than age_bottom",
              "age_bottom": "A valid age - must be used with age_top and be greater than age_top",
              "format": "Desired output format"
            },
            "output_formats": ["geojson", "topojson"],
            "examples": ["/api/fossils?interval_name=Permian",  "/api/fossils?age=271", "/api/fossils?age_top=200&age_bottom=250"]
          });
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
        larkin.error(res, next);
      } else {
        dbgeo.parse({
          "data": results,
          "outputFormat": (api.acceptedFormats.geo[req.query.format]) ? req.query.format : "geojson",
          "geometryColumn": "geometry",
          "geometryType": "wkt",
          "callback": function(error, result) {
            if (error) {
              larkin.log("error", error);
              larkin.error(res, next);
            } else {
              larkin.sendData(result, res, null, next);
            }
          }
        });
      }
    });
  });

/*    /api/strats?interval_name=Permian || /api/strats?age=250 || /api/strats?age_top=100&age_bottom=200    */
/* NB: this route needs updated to be like /readonly/getmap/geojson_macro5.php */
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
          larkin.error(res, next, "You must specify an age argument to get a result. NB: this version does NOT use continuous time age model for units. Therefore an age may return units that are not of that exact age but in a bin spanning that age.", {
            "parameters": {
              "interval_name": "The name of a time interval",
              "age": "A valid age",
              "age_top": "A valid age - must be used with age_bottom and be less than age_bottom",
              "age_bottom": "A valid age - must be used with age_top and be greater than age_top",
              "format": "Desired output format"
            },
            "output_formats": ["geojson", "topojson"],
            "examples": ["/api/strats?interval_name=Permian",  "/api/strats?age=271", "/api/strats?age_top=200&age_bottom=250"]
          });
        }
      },
      function(data, callback) {
        larkin.query("SELECT col_areas.col_id, cols.col_area AS area, AsWKT(col_areas.col_area) AS wkt, \
          GROUP_CONCAT(units.id SEPARATOR '|') AS units \
          FROM col_areas \
          JOIN cols ON cols.id = col_areas.col_id \
          JOIN units_sections ON units_sections.col_id = cols.id \
          JOIN units ON unit_id = units.id \
          JOIN intervals f ON f.id = FO \
          JOIN intervals l ON l.id = LO \
          WHERE f.age_bottom > ? AND l.age_top < ? AND status_code = 'active' \
          GROUP BY col_areas.col_id", [data.age_top, data.age_bottom], function(error, result) {
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
          "outputFormat": (api.acceptedFormats.geo[req.query.format]) ? req.query.format : "geojson",
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
          JOIN cols ON cols.id = col_id \
          JOIN projects ON projects.id = project_id \
          LEFT JOIN pbdb_matches ON unit_id = units.id \
            WHERE project IN ('North America','New Zealand','Caribbean','Deep Sea') and status_code='active' \
          GROUP BY project_id \
          ORDER BY field(project, 'North America','Caribbean','New Zealand','Deep Sea') ";

    var format = (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json";

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

    var format = (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json";
    larkin.query(sql, [], null, true, res, format, next);
  });

/*     /api/lith_definitions     */
api.route("/lithatt_definitions")
  .get(function(req, res, next) {
    var sql = "SELECT id,lith_att,att_type from lith_atts";
    var format = (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json";

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

    var format = (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json";
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
    var format = (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json";

    larkin.query(sql, params, null, true, res, format, next);
  });

/*    /api/strat_names    */
api.route("/strat_names")
  .get(function(req, res, next) {
    var filterString = "",
        params = [];

    if (req.query.id) {
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

    var sql = "SELECT strat_name name, rank, strat_name_id id, bed_name bed,bed_id,mbr_name mbr,mbr_id,fm_name fm,fm_id,gp_name gp,gp_id,sgp_name sgp,sgp_id FROM lookup_strat_names" + filterString;

    var format = (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json";

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

    var format = (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json";

    larkin.query(sql, [], null, true, res, format, next);
  });


/*    /api/paleogeography?year=550   /api/paleogeography?interval=Permian */
api.route("/paleogeography")
  .get(function(req, res, next) {
    if (!req.query.age && !req.query.interval_name) {
      larkin.error(res, next, "Please specify an or time interval", {
        "parameters": {
          "age": "Can be between 0 and 550",
          "interval_name": "A named time interval",
          "format": "Desired output format"
        },
        "output_formats": ["geojson", "topojson"],
        "examples": ["/api/paleogeography?interval_name=Permian",  "/api/paleogeography?age=271"]
      });
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
            "outputFormat": (api.acceptedFormats.geo[req.query.format]) ? req.query.format : "geojson",
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
