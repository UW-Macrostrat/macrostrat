var api = require("./api"),
    dbgeo = require("dbgeo"),
    async = require("async"),
    larkin = require("./larkin");

module.exports = function(req, res, next) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  } else {
    var geo = (req.query.format && api.acceptedFormats.geo[req.query.format]) ? true : false;

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
        } else if (req.query.unit_id || req.query.col_id || req.query.col_group_id || req.query.strat_name_id || req.query.strat_name_concept_id || "sample" in req.query) {
          callback(null, {"interval_name": "Unknown", "age_bottom": null, "age_top": null});
        } else {
          larkin.error(req, res, next, "Invalid parameters");
        }
      },
      function(data, callback) {
        var where = "",
            limit = ("sample" in req.query) ? " LIMIT 5" : "",
            params = {};

        if (data.age_bottom) {
          where += " AND b_age > :age_top AND t_age < :age_bottom";
          params["age_top"] = data.age_top;
          params["age_bottom"] = data.age_bottom;
        }

        if (req.query.unit_id) {
          where += " AND pbdb_matches.unit_id IN (:unit_id)";
          params["unit_id"] = larkin.parseMultipleIds(req.query.unit_id);

        } else if (req.query.col_id) {
          where += " AND units_sections.col_id IN (:col_id)";
          params["col_id"] = larkin.parseMultipleIds(req.query.col_id);
        }

        if (req.query.strat_name_id) {
          where += " AND (lookup_strat_names.bed_id IN (:strat_name_ids) OR lookup_strat_names.mbr_id IN (:strat_name_ids) OR lookup_strat_names.fm_id IN (:strat_name_ids) OR lookup_strat_names.gp_id IN (:strat_name_ids) OR lookup_strat_names.sgp_id IN (:strat_name_ids)) ";
          params["strat_name_ids"] = larkin.parseMultipleIds(req.query.strat_name_id);
        }

        if (req.query.strat_name_concept_id) {
          where += " AND lookup_strat_names.strat_name_id IN (SELECT strat_name_id FROM lookup_strat_names WHERE concept_id IN (:concept_id))";
          params["concept_id"] = larkin.parseMultipleIds(req.query.strat_name_concept_id);
        }

        if (req.query.col_group_id) {
          where += " AND col_group_id IN (:col_group_ids)";
          params["col_group_ids"] = larkin.parseMultipleIds(req.query.col_group_id);
        }

        larkin.query("SELECT pbdb_matches.collection_no AS cltn_id, collection_name AS cltn_name, t_age, b_age, n_occs AS pbdb_occs, \
          pbdb_matches.unit_id, CONCAT(pbdb_matches.ref_id, '|') AS refs " + ((geo) ? ", AsWKT(pbdb_matches.coordinate) AS geometry" : "") + " \
          FROM pbdb_matches \
          JOIN units ON pbdb_matches.unit_id = units.id \
          JOIN units_sections ON units_sections.unit_id = units.id \
          JOIN cols ON cols.id = units_sections.col_id \
          JOIN lookup_unit_intervals ON units_sections.unit_id=lookup_unit_intervals.unit_id \
          JOIN pbdb.coll_matrix ON pbdb_matches.collection_no = pbdb.coll_matrix.collection_no \
          LEFT JOIN unit_strat_names ON unit_strat_names.unit_id = units.id \
          LEFT JOIN lookup_strat_names ON lookup_strat_names.strat_name_id=unit_strat_names.strat_name_id \
          WHERE pbdb_matches.release_date < now() AND \
          status_code = 'active' " + where + limit, params, function(error, result) {
            if (error) {
              callback(error);
            } else {
              result.forEach(function(d) {
                d.refs = larkin.jsonifyPipes(d.refs, "integers");
                if (req.query.format && req.query.format === "csv") {
                    d.refs = d.refs.join("|")
                }
              });
              callback(null, data, result);
            }
        });
      }
    ], function(error, data, results) {
      if (error) {
        console.log(error);
        larkin.error(req, res, next, "Something went wrong");
      } else {
        if (geo) {
          dbgeo.parse({
            "data": results,
            "outputFormat": larkin.getOutputFormat(req.query.format),
            "geometryColumn": "geometry",
            "geometryType": "wkt"
          }, function(error, result) {
              if (error) {
                larkin.error(req, res, next, "Something went wrong");
              } else {
                larkin.sendData(req, res, next, {
                  format: (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json",
                  bare: (api.acceptedFormats.bare[req.query.format]) ? true : false,
                  refs: "refs"
                }, {
                  data: result
                });
              }
            }
          );
        } else {
          larkin.sendData(req, res, next, {
            format: (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json",
            refs: "refs"
          }, {
            data: results
          });
        }
      }
    });
  }
}
