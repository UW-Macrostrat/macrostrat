var api = require("./api"),
  dbgeo = require("dbgeo"),
  async = require("async"),
  larkin = require("./larkin");

module.exports = function (req, res, next) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  } else {
    var geo =
      req.query.format && api.acceptedFormats.geo[req.query.format]
        ? true
        : false;

    async.waterfall(
      [
        function (callback) {
          if (req.query.age_top && req.query.age_bottom) {
            callback(null, {
              interval_name: "Unknown",
              age_bottom: req.query.age_bottom,
              age_top: req.query.age_top,
            });
          } else if (req.query.age) {
            callback(null, {
              interval_name: "Unknown",
              age_bottom: req.query.age,
              age_top: req.query.age,
            });
          } else if (
            req.query.unit_id ||
            req.query.col_id ||
            req.query.col_group_id ||
            req.query.strat_name_id ||
            req.query.strat_name_concept_id ||
            "sample" in req.query
          ) {
            callback(null, {
              interval_name: "Unknown",
              age_bottom: null,
              age_top: null,
            });
          } else if (
            req.query.interval_name ||
            req.query.int_id ||
            req.query.lith_id ||
            req.query.lith ||
            req.query.lith_type ||
            req.query.lith_class ||
            req.query.environ_id ||
            req.query.environ ||
            req.query.environ_type ||
            req.query.environ_class ||
            req.query.econ_id ||
            req.query.econ ||
            req.query.econ_type ||
            req.query.econ_class
          ) {
            require("./units")(req, null, null, function (error, result) {
              if (error) {
                callback(error);
              }
              if (!result || !result.length) {
                return callback(null, null);
              }
              req.query.unit_id = result
                .map(function (d) {
                  return d.unit_id;
                })
                .join(",");
              callback(null, {
                interval_name: "Unknown",
                age_bottom: null,
                age_top: null,
              });
            });
          } else {
            larkin.error(req, res, next, "Invalid parameters");
          }
        },
        function (data, callback) {
          var where = "",
            limit = "sample" in req.query ? " LIMIT 5" : "",
            params = {};

          if (data.age_bottom) {
            where +=
              " AND lookup_unit_intervals.b_age > :age_top AND lookup_unit_intervals.t_age < :age_bottom";
            params["age_top"] = data.age_top;
            params["age_bottom"] = data.age_bottom;
          }

          if (req.query.unit_id) {
            where += " AND pbdb_matches.unit_id = ANY(:unit_id)";
            params["unit_id"] = larkin.parseMultipleIds(req.query.unit_id);
          } else if (req.query.col_id) {
            where += " AND units_sections.col_id = ANY(:col_id)";
            params["col_id"] = larkin.parseMultipleIds(req.query.col_id);
          }

          if (req.query.strat_name_id) {
            where +=
              " AND (lookup_strat_names.bed_id = ANY(:strat_name_ids) OR lookup_strat_names.mbr_id = ANY(:strat_name_ids) OR lookup_strat_names.fm_id = ANY(:strat_name_ids) OR lookup_strat_names.gp_id = ANY(:strat_name_ids) OR lookup_strat_names.sgp_id = ANY(:strat_name_ids)) ";
            params["strat_name_ids"] = larkin.parseMultipleIds(
              req.query.strat_name_id,
            );
          }

          if (req.query.strat_name_concept_id) {
            where +=
              " AND lookup_strat_names.strat_name_id = ANY(SELECT strat_name_id FROM lookup_strat_names WHERE concept_id = ANY(:concept_id))";
            params["concept_id"] = larkin.parseMultipleIds(
              req.query.strat_name_concept_id,
            );
          }

          if (req.query.col_group_id) {
            where += " AND col_group_id = ANY(:col_group_ids)";
            params["col_group_ids"] = larkin.parseMultipleIds(
              req.query.col_group_id,
            );
          }

          if (req.query.project_id) {
            where += " AND cols.project_id = ANY(:project_ids)";
            params["project_ids"] = larkin.parseMultipleIds(
              req.query.project_id,
            );
          }
          //TODO there is no pbdb table, so I removed LEFT JOIN pbdb.occ_matrix ON pbdb.coll_matrix.collection_no = pbdb.occ_matrix.collection_no
          //I also removed           LEFT JOIN pbdb.taxon_lower ON pbdb.occ_matrix.orig_no = pbdb.taxon_lower.orig_no
          //removed           JOIN pbdb.coll_matrix ON pbdb_matches.collection_no = pbdb.coll_matrix.collection_no

          //need dump and restore of pbdb or a copy of only the tables needed for the api to function in postgresql
          //find number of routes affected
          //find mariadb endpoint notes
          //"genus_no": [], "taxon_no": "" are always null
          larkin.queryPg("burwell",
            "SELECT pbdb_matches.collection_no AS cltn_id, collection_name AS cltn_name, lookup_unit_intervals.t_age, lookup_unit_intervals.b_age, n_occs AS pbdb_occs, COALESCE(GROUP_CONCAT(distinct pbdb.taxon_lower.genus_no), '') AS genus_no,  COALESCE(GROUP_CONCAT(distinct pbdb.occ_matrix.taxon_no), '') AS taxon_no, \
          pbdb_matches.unit_id, cols.id as col_id, CONCAT(pbdb_matches.ref_id, '|') AS refs " +
              (geo ? ", AsWKT(pbdb_matches.coordinate) AS geometry" : "") +
              ", lookup_strat_names.concept_id AS strat_name_concept_id \
          FROM macrostrat.pbdb_matches \
          JOIN macrostrat.units ON pbdb_matches.unit_id = units.id \
          JOIN macrostrat.units_sections ON units_sections.unit_id = units.id \
          JOIN macrostrat.cols ON cols.id = units_sections.col_id \
          JOIN macrostrat.lookup_unit_intervals ON units_sections.unit_id=lookup_unit_intervals.unit_id \
          LEFT JOIN macrostrat.unit_strat_names ON unit_strat_names.unit_id = units.id \
          LEFT JOIN macrostrat.lookup_strat_names ON lookup_strat_names.strat_name_id=unit_strat_names.strat_name_id \
          WHERE macrostrat.pbdb_matches.release_date < now() AND \
          macrostrat.cols.status_code = 'active' " +
              where +
              " GROUP BY pbdb_matches.collection_no" +
              limit,
            params,
            function (error, result) {
              if (error) {
                callback(error);
              } else {
                result.forEach(function (d) {
                  d.genus_no = d.genus_no.length
                    ? d.genus_no.split(",").map(function (d) {
                        return parseInt(d);
                      })
                    : [];
                  d.refs = larkin.jsonifyPipes(d.refs, "integers");
                  if (req.query.format && req.query.format === "csv") {
                    d.refs = d.refs.join("|");
                    d.genus_no = d.genus_no.join("|");
                  }
                });
                callback(null, data, result);
              }
            },
          );
        },
      ],
      function (error, data, results) {
        if (error) {
          console.log(error);
          larkin.error(req, res, next, "Something went wrong");
        } else {
          if (geo) {
            dbgeo.parse(
              results,
              {
                outputFormat: larkin.getOutputFormat(req.query.format),
                geometryColumn: "geometry",
                geometryType: "wkt",
              },
              function (error, result) {
                if (error) {
                  larkin.error(req, res, next, "Something went wrong");
                } else {
                  larkin.sendData(
                    req,
                    res,
                    next,
                    {
                      format: api.acceptedFormats.standard[req.query.format]
                        ? req.query.format
                        : "json",
                      bare: api.acceptedFormats.bare[req.query.format]
                        ? true
                        : false,
                      refs: "refs",
                    },
                    {
                      data: result,
                    },
                  );
                }
              },
            );
          } else {
            larkin.sendData(
              req,
              res,
              next,
              {
                format: api.acceptedFormats.standard[req.query.format]
                  ? req.query.format
                  : "json",
                refs: "refs",
              },
              {
                data: results,
              },
            );
          }
        }
      },
    );
  }
};
