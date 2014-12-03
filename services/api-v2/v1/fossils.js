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
          WHERE f.age_bottom > ? AND l.age_top < ? AND pbdb_matches.release_date < now() AND \
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
    });
  }
}
