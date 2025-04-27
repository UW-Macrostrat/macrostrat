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
            "SELECT\n" +
              "   cols.id AS col_id,\n" +
              "    lookup_unit_liths.lith_short,\n" +
              "    units.strat_name,\n" +
              "    units.id as unit_id,\n" +
              "    units.fo,\n" +
              "    units.lo,\n" +
              "    lookup_unit_intervals.fo_period,\n" +
              "    lookup_unit_intervals.fo_age,\n" +
              "    lookup_unit_intervals.lo_period,\n" +
              "    lookup_unit_intervals.lo_age,\n" +
              "    lookup_unit_intervals.age\n" +
              "FROM\n" +
              "    macrostrat.cols\n" +
              "JOIN\n" +
              "    macrostrat.units ON units.col_id = cols.id\n" +
              "JOIN\n" +
              "    macrostrat.lookup_unit_liths ON lookup_unit_liths.unit_id = units.id\n" +
              "JOIN\n" +
              "    macrostrat.lookup_unit_intervals ON lookup_unit_intervals.unit_id = units.id\n" +
              "WHERE\n" +
              "    ST_Contains(cols.poly_geom, ST_GeomFromText($1, 4326))\n" +
              "    AND cols.status_code = 'active'\n" +
              "ORDER BY lo_age;",
            ["POINT(" + req.query.lng + " " + req.query.lat + ")"],
            function (error, result) {
              if (error) {
                callback(error);
              } else {
                if (result.rows.length > 0) {
                  const rocktypes = result.rows
                    .map((row) => {
                      // Split lith_short into parts and extract only the type
                      const lithParts = row.lith_short.split("|");
                      return lithParts.map((part) => {
                        const [type] = part
                          .split(" ")
                          .map((item) => item.trim()); // Extract only the type
                        return type; // Return the type as a string
                      });
                    })
                    .flat();
                  const median = result.rows.length / 2 - 1;
                  const col_id = result.rows[0].col_id;
                  const unit_age = result.rows[median].lo_period;
                  const unit_name = result.rows[median].strat_name;

                  larkin.trace(
                    "ROCKTYPE RESULTS",
                    result.rows,
                    "AND COL_ID ",
                    col_id,
                  );
                  const uniqueRocktypes = Array.from(new Set(rocktypes));
                  callback(null, {
                    gid: col_id,
                    rocktype: uniqueRocktypes,
                    unit_name: unit_name,
                    unit_age: unit_age,
                    unitdesc: "",
                  });
                } else {
                  callback(null, { rocktype: [] });
                }
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
                      larkin.trace("columns query result", result);
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
                        larkin.trace("final column query results ", result);
                        callbackB(null, result.rows[0]);
                      }
                    }
                  },
                );
              },

              function (column, callbackB) {
                var sql = `SELECT units.id AS unit_id, units.strat_name, period, max_thick, min_thick, colors.unit_class, count(distinct collection_no) pbdb_cltns, lith_short AS lith
                FROM macrostrat.units
                JOIN macrostrat.colors ON colors.color::text = units.color::text
                JOIN macrostrat.units_sections ON units_sections.unit_id = units.id
                JOIN macrostrat.lookup_unit_liths ON lookup_unit_liths.unit_id=units.id
                JOIN macrostrat.lookup_unit_intervals ON units.id=lookup_unit_intervals.unit_id
                LEFT JOIN macrostrat.unit_strat_names ON unit_strat_names.unit_id=units.id
                LEFT JOIN macrostrat.lookup_strat_names ON lookup_strat_names.strat_name_id=unit_strat_names.strat_name_id
                LEFT JOIN macrostrat.pbdb_matches ON pbdb_matches.unit_id=units.id and pbdb_matches.release_date < now()
                WHERE units_sections.col_id = $1
                GROUP BY units.id, period, unit_class, lith_short
                ORDER BY units.id ASC;`;

                larkin.queryPg(
                  "burwell",
                  sql,
                  [column.col_id],
                  function (error, result) {
                    if (error) {
                      callbackB(error);
                    } else {
                      result.rows.forEach(function (d) {
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
          larkin.trace(error);
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
              data: results,
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
                larkin.queryPg(
                  "burwell",
                  `
                SELECT units.id AS unit_id, units.strat_name, period, max_thick, min_thick, colors.unit_class, count(distinct collection_no) pbdb_cltns, lith_short AS lith
                FROM macrostrat.units
                JOIN macrostrat.colors ON colors.color::text = units.color::text
                JOIN macrostrat.units_sections ON units_sections.unit_id = units.id
                JOIN macrostrat.lookup_unit_liths ON lookup_unit_liths.unit_id=units.id
                JOIN macrostrat.lookup_unit_intervals ON units.id=lookup_unit_intervals.unit_id
                LEFT JOIN macrostrat.unit_strat_names ON unit_strat_names.unit_id=units.id
                LEFT JOIN macrostrat.lookup_strat_names ON lookup_strat_names.strat_name_id=unit_strat_names.strat_name_id
                LEFT JOIN macrostrat.pbdb_matches ON pbdb_matches.unit_id=units.id and pbdb_matches.release_date < now()
                WHERE units_sections.col_id = ?
                GROUP BY units.id, period, unit_class, lith_short
                ORDER BY units.id ASC;`,
                  [req.query.col_id],
                  function (error, result) {
                    if (error) {
                      callbackB(error);
                    } else {
                      result.rows.forEach(function (d) {
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
          larkin.trace(error);
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
              data: results,
            },
          );
        }
      },
    );
  } else {
    larkin.info(req, res, next);
  }
};
