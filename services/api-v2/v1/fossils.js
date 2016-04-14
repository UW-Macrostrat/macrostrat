var api = require("./api"),
    dbgeo = require("dbgeo"),
    async = require("async"),
    larkin = require("./larkin");

module.exports = function(req, res, next) {
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
        } else if (req.query.unit_id || req.query.col_id) {
          callback(null, {"interval_name": "Unknown", "age_bottom": null, "age_top": null});
        } else {
          larkin.error(req, res, next, "Invalid parameters");
        }
      },
      function(data, callback) {
        var where,
            params = [];

        if (data.age_bottom) {
          where = " AND f.age_bottom > ? AND l.age_top < ?";
          params.push(data.age_top, data.age_bottom);
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

            where = " AND pbdb_matches.unit_id IN (" + placeholders.join(",") + ")";

          } else {
            where = " AND pbdb_matches.unit_id = ?";
            params.push(req.query.unit_id);
          }

        } else if (req.query.col_id) {
          if (req.query.col_id.indexOf(",") > -1) {
            var ids = req.query.col_id.split(","),
                placeholders = [];
            
            ids = ids.map(function(d) {
              return parseInt(d);
            });

            for (var i = 0; i < ids.length; i++) {
              placeholders.push("?");
              params.push(ids[i]);
            }

            where = " AND units_sections.col_id IN (" + placeholders.join(",") + ")";

          } else {
            where = " AND units_sections.col_id = ?";
            params.push(req.query.col_id);
          }
        }

        // TODO: v2 clean up 89!!!

        larkin.query("SELECT pbdb_matches.collection_no, n_occs AS occ, \
          pbdb_matches.unit_id " + ((!req.query.format || req.query.format != "json") ? ", AsWKT(pbdb_matches.coordinate) AS geometry" : "") + " \
          FROM pbdb_matches \
          JOIN units ON pbdb_matches.unit_id = units.id \
          JOIN units_sections ON units_sections.unit_id = units.id \
          JOIN cols ON cols.id = units_sections.col_id \
          JOIN intervals f ON f.id = FO \
          JOIN intervals l ON l.id = LO \
          JOIN pbdb.coll_matrix ON pbdb_matches.collection_no = pbdb.coll_matrix.collection_no \
          WHERE pbdb_matches.release_date < now() AND \
          status_code = 'active'" + where, params, function(error, result) {
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

    // TODO: v2 clean this up (too much self loathing...)
        if (req.query.format && req.query.format === "json") {
          larkin.sendData(results, res, null, next);
        } else {
          dbgeo.parse({
            "data": results,
            "outputFormat": larkin.getOutputFormat(req.query.format),
            "geometryColumn": "geometry",
            "geometryType": "wkt",
            "callback": function(error, result) {
              if (error) {
                larkin.error(req, res, next, "Something went wrong");
              } else {
                if (api.acceptedFormats.bare[req.query.format]) {
                  larkin.sendBare(result, res, next);
                } else {
                  larkin.sendData(result, res, null, next);
                }
              }
            }
          });
        }
      }
    });
  }
}
