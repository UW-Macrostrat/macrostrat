var api = require("../api"),
  async = require("async"),
  wellknown = require("wellknown"),
  gp = require("geojson-precision"),
  larkin = require("../larkin");

module.exports = function (req, res, next) {
  if (req.query.lat && req.query.lng) {
    async.parallel(
      {
        gmus: function (callback) {
          larkin.queryPg(
            "geomacro",
            "SELECT gid, (SELECT array_agg(DISTINCT rocktypes) FROM unnest(array[rocktype1, rocktype2, u_rocktype1, u_rocktype2, u_rocktype3]) rocktypes WHERE rocktypes IS NOT null) AS rocktype, unit_name, unit_age, unitdesc FROM gmus.lookup_units WHERE ST_Contains(geom, ST_GeomFromText($1, 4326))",
            ["POINT(" + req.query.lng + " " + req.query.lat + ")"],
            function (error, result) {
              if (error) {
                callback(error);
              } else {
                callback(null, result.rows[0]);
              }
            },
          );
        },

        column: function (callback) {
          async.waterfall(
            [
              function (callbackB) {
                // Find nearest column
                larkin.queryPg(
                  "geomacro",
                  "SELECT id AS col_id, col_name, ST_AsGeoJSON(poly_geom) AS col_poly FROM macrostrat.cols WHERE ST_Contains(poly_geom, ST_GeomFromText($1, 4326)) and status_code='active'",
                  ["POINT(" + req.query.lng + " " + req.query.lat + ")"],
                  function (error, result) {
                    if (error) {
                      callback(error);
                    } else {
                      /* If a column isn't immediately found, buffer the point by a degree, get all polygons that
                   intersect that buffer, and then find the closest one */
                      if (result.rows.length < 1) {
                        larkin.queryPg(
                          "geomacro",
                          "SELECT id AS col_id, col_name, ST_AsGeoJSON(poly_geom) AS col_poly FROM macrostrat.cols WHERE ST_Intersects(poly_geom, ST_Buffer(ST_GeomFromText($1, 4326), 1)) and status_code='active' ORDER BY ST_Distance(ST_GeomFromText($1, 4326), poly_geom) LIMIT 1",
                          [
                            "POINT(" +
                              req.query.lng +
                              " " +
                              req.query.lat +
                              ")",
                          ],
                          function (error, result) {
                            if (error) {
                              callback(error);

                              // If no columns are found within 1 degree, return an empty result
                            } else if (result.rows.length < 1) {
                              callbackB([]);
                            } else {
                              // Otherwise return the closest one
                              callbackB(null, result.rows[0]);
                            }
                          },
                        );
                      } else {
                        callbackB(null, result.rows[0]);
                      }
                    }
                  },
                );
              },

              function (column, callbackB) {
                var sql =
                  `SELECT units.id AS unit_id, units.strat_name, period, max_thick, min_thick, colors.unit_class, count(distinct collection_no) pbdb_cltns, lith_short AS lith
                FROM macrostrat_temp.units
                JOIN macrostrat_temp.colors ON colors.color::text = units.color::text
                JOIN macrostrat_temp.units_sections ON units_sections.unit_id = units.id
                JOIN macrostrat_temp.lookup_unit_liths ON lookup_unit_liths.unit_id=units.id
                JOIN macrostrat_temp.lookup_unit_intervals ON units.id=lookup_unit_intervals.unit_id
                LEFT JOIN macrostrat_temp.unit_strat_names ON unit_strat_names.unit_id=units.id
                LEFT JOIN macrostrat_temp.lookup_strat_names ON lookup_strat_names.strat_name_id=unit_strat_names.strat_name_id
                LEFT JOIN macrostrat_temp.pbdb_matches ON pbdb_matches.unit_id=units.id and pbdb_matches.release_date < now()
                WHERE units_sections.col_id = ?
                GROUP BY units.id, period, unit_class, lith_short
                ORDER BY units.id ASC;`

                larkin.queryPg("burwell", sql, [column.col_id], function (error, result) {
                  if (error) {
                    callbackB(error);
                  } else {
                    result.forEach(function (d) {
                      d.lith = larkin.fixLiths(d.lith);
                    });

                    callbackB(null, column, result.rows);
                  }
                });
              },
            ],
            // after the two queries are executed, send the result
            function (err, column, units) {
              if (err) {
                if (err.length === 0) {
                  callback(null, {});
                } else {
                  callback(err);
                }
              } else {
                var col = [
                  {
                    col_id: column.col_id,
                    col_name: column.col_name,
                    col_poly:
                      req.query.geo_format === "wkt"
                        ? wellknown.stringify(
                            gp(JSON.parse(column.col_poly), 3),
                          )
                        : gp(JSON.parse(column.col_poly), 3),
                    units: units,
                  },
                ];
                callback(null, col[0]);
              }
            },
          );
        },
      },
      function (error, results) {
        if (error) {
          console.log(error);
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
              bare: api.acceptedFormats.bare[req.query.format] ? true : false,
              compact: true,
            },
            {
              data: [results.rows],
            },
          );
        }
      },
    );
  } else if (req.query.col_id && req.query.unit_id) {
    async.parallel(
      {
        gmus: function (callback) {
          larkin.queryPg(
            "geomacro",
            "SELECT gid, (SELECT array_agg(DISTINCT rocktypes) FROM unnest(array[rocktype1, rocktype2, u_rocktype1, u_rocktype2, u_rocktype3]) rocktypes WHERE rocktypes IS NOT null) AS rocktype, unit_name, unit_age, unitdesc FROM gmus.lookup_units WHERE gid = $1",
            [req.query.unit_id],
            function (error, result) {
              if (error) {
                callback(error);
              } else {
                callback(null, result.rows[0]);
              }
            },
          );
        },

        column: function (callback) {
          async.waterfall(
            [
              function (callbackB) {
                larkin.queryPg(
                  "geomacro",
                  "SELECT id AS col_id, col_name, ST_AsGeoJSON(poly_geom) AS col_poly FROM macrostrat.cols WHERE id = $1",
                  [req.query.col_id],
                  function (error, result) {
                    if (error) {
                      callbackB(error);
                    } else {
                      if (result.rows.length === 0) {
                        callback(null);
                      } else {
                        callbackB(null, result.rows[0]);
                      }
                    }
                  },
                );
              },

              function (column, callbackB) {
                larkin.queryPg("burwell",
                    `
                SELECT units.id AS unit_id, units.strat_name, period, max_thick, min_thick, colors.unit_class, count(distinct collection_no) pbdb_cltns, lith_short AS lith
                FROM macrostrat_temp.units
                JOIN macrostrat_temp.colors ON colors.color::text = units.color::text
                JOIN macrostrat_temp.units_sections ON units_sections.unit_id = units.id
                JOIN macrostrat_temp.lookup_unit_liths ON lookup_unit_liths.unit_id=units.id
                JOIN macrostrat_temp.lookup_unit_intervals ON units.id=lookup_unit_intervals.unit_id
                LEFT JOIN macrostrat_temp.unit_strat_names ON unit_strat_names.unit_id=units.id
                LEFT JOIN macrostrat_temp.lookup_strat_names ON lookup_strat_names.strat_name_id=unit_strat_names.strat_name_id
                LEFT JOIN macrostrat_temp.pbdb_matches ON pbdb_matches.unit_id=units.id and pbdb_matches.release_date < now()
                WHERE units_sections.col_id = ?
                GROUP BY units.id, period, unit_class, lith_short
                ORDER BY units.id ASC;`,
                  [req.query.col_id],
                  function (error, result) {
                    if (error) {
                      callbackB(error);
                    } else {
                      result.forEach(function (d) {
                        d.lith = larkin.fixLiths(d.lith);
                      });

                      callbackB(null, column, result.rows);
                    }
                  },
                );
              },
            ],
            // after the two queries are executed, send the result
            function (err, column, units) {
              if (err) {
                callback(err);
              } else {
                var col = [
                  {
                    col_id: column.col_id,
                    col_name: column.col_name,
                    col_poly:
                      req.query.geo_format === "wkt"
                        ? wellknown.stringify(
                            gp(JSON.parse(column.col_poly), 3),
                          )
                        : gp(JSON.parse(column.col_poly), 3),
                    units: units,
                  },
                ];
                callback(null, col[0]);
              }
            },
          );
        },
      },
      function (error, results) {
        if (error) {
          console.log(error);
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
              bare: api.acceptedFormats.bare[req.query.format] ? true : false,
              compact: true,
            },
            {
              data: [results.rows],
            },
          );
        }
      },
    );
  } else {
    larkin.info(req, res, next);
  }
};
