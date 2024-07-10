var api = require("./api"),
  async = require("async"),
  dbgeo = require("dbgeo"),
  gp = require("geojson-precision"),
  larkin = require("./larkin");

module.exports = function (req, res, next, cb) {
  // If no parameters, send the route definition
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }
  let params = {}


  // First determine age range component of query, if any.
  // NB: ORDER MATTERS here. Do NOT add else if statements before req.query.interval_name, req.query.age or req.query.age_top else statements or  those age parameters will be ommitted
  async.waterfall(
    [
      function (callback) {
        if (req.query.interval_name) {
          //params.push(req.query.interval_name)
          params["interval_name"] = [req.query.interval_name];
          let sql = `SELECT age_bottom, age_top, interval_name FROM macrostrat_temp.intervals WHERE interval_name = ${params["interval_name"]} LIMIT 1`
          larkin.queryPgMaria("macrostrat_two",
            sql,
            params,
            function (error, result) {
              if (error) {
                callback(error);
              } else {
                if (result.rowCount == 0) {
                  return larkin.error(req, res, next, "No results found");
                } else {
                  callback(null, {
                    interval_name: result.rows[0].interval_name,
                    age_bottom: result.rows[0].age_bottom,
                    age_top: result.rows[0].age_top,
                  });
                }
              }
            },
          );
        } else if (req.query.int_id) {
          let sql = "SELECT age_bottom, age_top, interval_name FROM macrostrat_temp.intervals WHERE id = $1 LIMIT 1"
          params.push(req.query.int_id)
          larkin.queryPgMaria("macrostrat_two",
            sql,
            params,
            function (error, result) {
              if (error) {
                callback(error);
              } else {
                if (result.rowCount == 0) {
                  callback(null, {
                    interval_name: "none",
                    age_bottom: 0,
                    age_top: 9999999,
                  });
                } else {
                  callback(null, {
                    interval_name: result.rows[0].interval_name,
                    age_bottom: result.rows[0].age_bottom,
                    age_top: result.rows[0].age_top,
                  });
                }
              }
            },
          );
        } else if (req.query.age) {
          callback(null, {
            interval_name: "none",
            age_bottom: req.query.age,
            age_top: req.query.age,
          });
        } else if (req.query.age_top && req.query.age_bottom) {
          callback(null, {
            interval_name: "none",
            age_bottom: req.query.age_bottom,
            age_top: req.query.age_top,
          });
        } else if (req.query.shape) {
          larkin.queryPg(
            "burwell",
            `
          SELECT id
          FROM macrostrat.cols
          WHERE ST_Intersects(poly_geom, ST_GeomFromText($1, 4326))
        `,
            [req.query.shape],
            function (error, response) {
              if (error) return callback(error);

              callback(null, {
                interval_name: "none",
                age_bottom: 99999,
                age_top: 0,
                col_ids: response.rows.map(function (d) {
                  return d.id;
                }),
              });
            },
          );
        } else if (req.query.lat && req.query.lng) {
          var sql =
            req.query.adjacents === "true"
              ? "WITH containing_geom AS (SELECT poly_geom FROM macrostrat.cols WHERE ST_Contains(poly_geom, ST_GeomFromText($1, 4326))) SELECT id FROM macrostrat.cols WHERE ST_Intersects((SELECT * FROM containing_geom), poly_geom) ORDER BY ST_Distance(ST_Centroid(poly_geom), ST_GeomFromText($1, 4326))"
              : "SELECT id FROM macrostrat.cols WHERE ST_Contains(poly_geom, st_setsrid(ST_GeomFromText($1), 4326)) ORDER BY ST_Distance(ST_Centroid(poly_geom), ST_GeomFromText($1, 4326))";

          larkin.queryPg(
            "burwell",
            sql,
            [
              "POINT(" +
                larkin.normalizeLng(req.query.lng) +
                " " +
                req.query.lat +
                ")",
            ],
            function (error, response) {
              if (error) {
                callback(error);
              } else {
                callback(null, {
                  interval_name: "none",
                  age_bottom: 99999,
                  age_top: 0,
                  col_ids: response.rows.map(function (d) {
                    return d.id;
                  }),
                });
              }
            },
          );
        } else if (req.query.col_id && req.query.adjacents) {
          var col_ids = larkin.parseMultipleIds(req.query.col_id),
            placeholders = col_ids.map(function (d, i) {
              return "$" + (i + 1);
            });

          var sql =
            "WITH containing_geom AS (SELECT poly_geom FROM macrostrat.cols WHERE id IN (" +
            placeholders.join(",") +
            ")) SELECT id FROM macrostrat.cols WHERE ST_Intersects((SELECT * FROM containing_geom), poly_geom)";

          if (col_ids.length === 1) {
            sql +=
              " ORDER BY ST_Distance(ST_Centroid(poly_geom), (SELECT * FROM containing_geom))";
          }

          larkin.queryPg("burwell", sql, col_ids, function (error, response) {
            if (error) {
              callback(error);
            } else {
              callback(null, {
                interval_name: "none",
                age_bottom: 99999,
                age_top: 0,
                col_ids: response.rows.map(function (d) {
                  return d.id;
                }),
              });
            }
          });
        } else if (req.query.col_group_id) {
          larkin.query(
            "SELECT id FROM cols WHERE col_group_id IN (:col_group_ids)",
            { col_group_ids: larkin.parseMultipleIds(req.query.col_group_id) },
            function (error, data) {
              callback(null, {
                interval_name: "none",
                age_bottom: 99999,
                age_top: 0,
                col_ids: data.map(function (d) {
                  return d.id;
                }),
              });
            },
          );
        } else if (req.query.strat_name) {
          larkin.query(
            "SELECT strat_name_id FROM lookup_strat_names WHERE strat_name LIKE ? ",
            ["%" + req.query.strat_name + "%"],
            function (error, result) {
              if (error) {
                callback(error);
              } else {
                if (result.length === 0) {
                  return larkin.error(req, res, next, "No results found");
                } else {
                  var ids = result.map(function (d) {
                    return d.strat_name_id;
                  });
                  callback(null, {
                    interval_name: "none",
                    age_bottom: 99999,
                    age_top: 0,
                    strat_ids: ids,
                  });
                }
              }
            },
          );
        } else if (req.query.strat_name_concept_id) {
          larkin.query(
            "SELECT id FROM strat_names WHERE concept_id IN (:strat_name_concept_ids) ",
            {
              strat_name_concept_ids: larkin.parseMultipleIds(
                req.query.strat_name_concept_id,
              ),
            },
            function (error, result) {
              if (error) {
                callback(error);
              } else {
                if (result.length === 0) {
                  callback(null, {
                    interval_name: "none",
                    age_bottom: 99999,
                    age_top: 0,
                    strat_ids: [null],
                  });
                  //return larkin.error(req, res, next, "No results found");
                } else {
                  var ids = result.map(function (d) {
                    return d.id;
                  });
                  callback(null, {
                    interval_name: "none",
                    age_bottom: 99999,
                    age_top: 0,
                    strat_ids: ids,
                  });
                }
              }
            },
          );
        } else if (req.query.strat_name_id) {
          var ids = larkin.parseMultipleIds(req.query.strat_name_id);
          callback(null, {
            interval_name: "none",
            age_bottom: 99999,
            age_top: 0,
            strat_ids: ids,
          });
        } else if (
          req.query.unit_id ||
          req.query.section_id ||
          req.query.col_id ||
          req.query.lith ||
          req.query.lith_id ||
          req.query.lith_class ||
          req.query.lith_type ||
          req.query.lith_group ||
          req.query.environ ||
          req.query.environ_id ||
          req.query.environ_class ||
          req.query.environ_type ||
          req.query.project_id ||
          "sample" in req.query ||
          "all" in req.query ||
          req.query.econ_id ||
          req.query.econ ||
          req.query.econ_type ||
          req.query.econ_class ||
          req.query.cltn_id ||
          req.query.lith_att_id ||
          req.query.lith_att ||
          req.query.lith_att_type ||
          req.query.col_type ||
          req.query.status_code
        ) {
          callback(null, {
            interval_name: "none",
            age_bottom: 99999,
            age_top: 0,
          });
        } else {
          callback("Invalid parameters passed");
        }
      },

      function (data, callback) {
        var where = "",
          limit = "sample" in req.query ? (cb ? " LIMIT 15 " : " LIMIT 5") : "",
          orderby = [],
          params = {};

        if (req.query.status_code) {
          where += "cols.status_code IN (:status_code)";
          params["status_code"] = larkin.parseMultipleStrings(
            decodeURI(req.query.status_code),
          );
        } else {
          where += "cols.status_code = 'active'";
        }

        if (
          req.query.lith ||
          req.query.lith_class ||
          req.query.lith_type ||
          req.query.lith_id ||
          req.query.lith_group
        ) {
          where +=
            " AND units.id IN (SELECT unit_liths.unit_id FROM unit_liths JOIN liths ON lith_id = liths.id WHERE ";
          var lithWhere = [];

          if (req.query.lith) {
            lithWhere.push("lith IN (:lith)");
            params["lith"] = larkin.parseMultipleStrings(req.query.lith);
          }

          if (req.query.lith_class) {
            lithWhere.push("lith_class IN (:lith_class)");
            params["lith_class"] = larkin.parseMultipleStrings(
              req.query.lith_class,
            );
          }

          if (req.query.lith_type) {
            lithWhere.push("lith_type IN (:lith_type)");
            params["lith_type"] = larkin.parseMultipleStrings(
              req.query.lith_type,
            );
          }

          if (req.query.lith_group) {
            lithWhere.push("lith_group IN (:lith_group)");
            params["lith_group"] = larkin.parseMultipleStrings(
              req.query.lith_group,
            );
          }

          if (req.query.lith_id) {
            lithWhere.push("liths.id IN (:lith_id)");
            params["lith_id"] = larkin.parseMultipleIds(req.query.lith_id);
          }

          where += lithWhere.join(" OR ") + ")";
        }

        if (
          req.query.lith_att_id ||
          req.query.lith_att ||
          req.query.lith_att_type
        ) {
          where += `
          AND units.id IN (
            SELECT unit_liths.unit_id
            FROM unit_liths
            JOIN liths ON lith_id = liths.id
            JOIN unit_liths_atts ON unit_liths_atts.unit_lith_id = unit_liths.id
            JOIN lith_atts ON unit_liths_atts.lith_att_id = lith_atts.id
            WHERE ::lith_att_field`;

          if (req.query.lith_att_id) {
            where += " IN (:lith_att)) ";
            params["lith_att_field"] = "unit_liths_atts.lith_att_id";
            params["lith_att"] = larkin.parseMultipleIds(req.query.lith_att_id);
          } else if (req.query.lith_att) {
            where += " IN (:lith_att)) ";
            params["lith_att_field"] = "lith_atts.lith_att";
            params["lith_att"] = larkin.parseMultipleStrings(
              req.query.lith_att,
            );
          } else if (req.query.lith_att_type) {
            where += " IN (:lith_att)) ";
            params["lith_att_field"] = "lith_atts.att_type";
            params["lith_att"] = larkin.parseMultipleStrings(
              req.query.lith_att_type,
            );
          }
        }

        if (data.age_bottom !== 99999) {
          where += " AND b_age > :age_top AND t_age < :age_bottom";
          params["age_top"] = data.age_top;
          params["age_bottom"] = data.age_bottom;
        }

        if (req.query.unit_id) {
          where += " AND units.id IN (:unit_ids)";
          params["unit_ids"] = larkin.parseMultipleIds(req.query.unit_id);
          orderby.push(
            "FIELD(units.id, " +
              larkin.parseMultipleIds(req.query.unit_id).join(",") +
              ")",
          );
        }

        if (req.query.section_id) {
          where += " AND units_sections.section_id IN (:section_ids)";
          params["section_ids"] = larkin.parseMultipleIds(req.query.section_id);
        }

        if ("col_ids" in data) {
          where += " AND units_sections.col_id IN (:col_ids)";
          if (!data.col_ids.length) {
            data.col_ids = [""];
          }
          params["col_ids"] = data.col_ids;
        } else if (req.query.col_id) {
          where += " AND units_sections.col_id IN (:col_ids)";
          params["col_ids"] = larkin.parseMultipleIds(req.query.col_id);
        }

        if (data.strat_ids) {
          where +=
            " AND (lookup_strat_names.bed_id IN (:strat_ids) OR lookup_strat_names.mbr_id IN (:strat_ids) OR lookup_strat_names.fm_id IN (:strat_ids) OR lookup_strat_names.gp_id IN (:strat_ids) OR lookup_strat_names.sgp_id IN (:strat_ids)) ";
          params["strat_ids"] = data.strat_ids;
        }

        if (req.query.project_id) {
          where += " AND lookup_units.project_id IN (:project_id)";
          params["project_id"] = larkin.parseMultipleIds(req.query.project_id);
        }

        if (
          req.query.environ_id ||
          req.query.environ ||
          req.query.environ_class ||
          req.query.environ_type
        ) {
          where +=
            " AND units.id IN (SELECT unit_environs.unit_id FROM unit_environs JOIN environs on environ_id=environs.id WHERE ";
          var environWhere = [];

          if (req.query.environ) {
            environWhere.push("environ IN (:environ)");
            params["environ"] = larkin.parseMultipleStrings(req.query.environ);
          }

          if (req.query.environ_class) {
            environWhere.push("environ_class IN (:environ_class)");
            params["environ_class"] = larkin.parseMultipleStrings(
              req.query.environ_class,
            );
          }

          if (req.query.environ_type) {
            environWhere.push("environ_type IN (:environ_type)");
            params["environ_type"] = larkin.parseMultipleStrings(
              req.query.environ_type,
            );
          }

          if (req.query.environ_id) {
            environWhere.push("environs.id IN (:environ_id)");
            params["environ_id"] = larkin.parseMultipleIds(
              req.query.environ_id,
            );
          }

          where += environWhere.join(" OR ") + ")";
        }

        if (
          req.query.econ_id ||
          req.query.econ ||
          req.query.econ_type ||
          req.query.econ_class
        ) {
          where +=
            " AND units.id IN (SELECT unit_econs.unit_id FROM unit_econs JOIN econs on econ_id=econs.id WHERE ::econ_field";

          if (req.query.econ_id) {
            where += " IN (:econ))";
            params["econ"] = larkin.parseMultipleIds(req.query.econ_id);
            params["econ_field"] = "econs.id";
          } else if (req.query.econ) {
            where += " IN (:econ))";
            params["econ"] = larkin.parseMultipleStrings(req.query.econ);
            params["econ_field"] = "econs.econ";
          }
          if (req.query.econ_type) {
            where += " IN (:econ))";
            params["econ"] = larkin.parseMultipleStrings(req.query.econ_type);
            params["econ_field"] = "econs.econ_type";
          }
          if (req.query.econ_class) {
            where += " IN (:econ))";
            params["econ"] = larkin.parseMultipleStrings(req.query.econ_class);
            params["econ_field"] = "econs.econ_class";
          }
        }

        if (req.query.cltn_id) {
          where +=
            " AND units.id IN (SELECT unit_id FROM pbdb_matches WHERE collection_no IN (:cltn_ids))";
          params["cltn_ids"] = larkin.parseMultipleIds(req.query.cltn_id);
        }

        if (req.query.col_type) {
          where += " AND cols.col_type IN (:col_type)";
          params["col_type"] = larkin.parseMultipleStrings(req.query.col_type);
        }

        if ("sample" in req.query) {
          // Speeds things up...
          where +=
            " AND units_sections.col_id IN (92, 488, 463, 289, 430, 481, 261, 534, 369, 798, 771, 1675) ";
        }

        params["measure_field"] =
          "summarize_measures" in req.query
            ? "lookup_unit_attrs_api.measure_long"
            : "lookup_unit_attrs_api.measure_short";

        var shortSQL = `
      units.id AS unit_id,
      units_sections.section_id AS section_id,
      units_sections.col_id AS col_id,
      cols.project_id,
      cols.col_area,
      units.strat_name AS unit_name,
      unit_strat_names.strat_name_id,
      IFNULL(mbr_name, '') AS Mbr,
      IFNULL(fm_name, '') AS Fm,
      IFNULL(gp_name, '') AS Gp,
      IFNULL(sgp_name, '') AS SGp,
      lookup_units.t_age,
      lookup_units.b_age,
      units.max_thick,
      units.min_thick,
      units.outcrop,
      lookup_units.pbdb_collections,
      lookup_units.pbdb_occurrences`;

        var longSQL = `${shortSQL},
      lookup_unit_attrs_api.lith,
      lookup_unit_attrs_api.environ,
      lookup_unit_attrs_api.econ,
      ::measure_field AS measure,
      IFNULL(notes, '') AS notes,
      lookup_units.color,
      lookup_units.text_color,
      lookup_units.t_int AS t_int_id,
      lookup_units.t_int_name,
      lookup_units.t_int_age,
      lookup_units.t_prop,
      lookup_units.units_above,
      lookup_units.b_int AS b_int_id,
      lookup_units.b_int_name,
      lookup_units.b_int_age,
      lookup_units.b_prop,
      lookup_units.units_below,
      lookup_strat_names.rank_name AS strat_name_long,
      GROUP_CONCAT(col_refs.ref_id SEPARATOR '|') AS refs
      `;
        if ("show_position" in req.query) {
          longSQL += ", position_top AS t_pos, position_bottom AS b_pos";
        }

        var geometry =
          (req.query.format && api.acceptedFormats.geo[req.query.format]) ||
          req.query.response === "long"
            ? ", lookup_units.clat, lookup_units.clng, lookup_units.t_plat, lookup_units.t_plng, lookup_units.b_plat, lookup_units.b_plng "
            : "";

        var sql = `
        SELECT ${req.query.response === "long" || cb ? longSQL : shortSQL} ${geometry}
        FROM units
        LEFT JOIN lookup_unit_attrs_api ON lookup_unit_attrs_api.unit_id = units.id
        LEFT JOIN lookup_units ON units.id = lookup_units.unit_id
        LEFT JOIN unit_strat_names ON unit_strat_names.unit_id=units.id
        LEFT JOIN units_sections ON units.id = units_sections.unit_id
        LEFT JOIN cols ON units_sections.col_id = cols.id
        LEFT JOIN col_refs ON cols.id = col_refs.col_id
        LEFT JOIN lookup_strat_names ON lookup_strat_names.strat_name_id=unit_strat_names.strat_name_id
        LEFT JOIN unit_notes ON unit_notes.unit_id=units.id
        WHERE
          ${where}
        GROUP BY units.id
      ORDER BY ${orderby.length > 0 ? orderby.join(", ") + "," : ""} t_age ASC
      ${limit}
      `;

        larkin.query(sql, params, function (error, result) {
          if (error) {
            console.log(error);
            callback(error);
          } else {
            if (req.query.response === "long" || cb) {
              for (var i = 0; i < result.length; i++) {
                // These come back as JSON strings, so we need to make them real JSON
                result[i].lith = JSON.parse(result[i].lith) || [];
                result[i].environ = JSON.parse(result[i].environ) || [];
                result[i].econ = JSON.parse(result[i].econ) || [];
                result[i].measure = JSON.parse(result[i].measure) || [];

                result[i].units_above = larkin.jsonifyPipes(
                  result[i].units_above,
                  "integers",
                );
                result[i].units_below = larkin.jsonifyPipes(
                  result[i].units_below,
                  "integers",
                );
                result[i].refs = larkin.jsonifyPipes(
                  result[i].refs,
                  "integers",
                );
              }
            }

            if (
              req.query.format === "csv" &&
              req.query.response === "long" &&
              !cb
            ) {
              for (var i = 0; i < result.length; i++) {
                result[i].units_above = result[i].units_above.join(",");
                result[i].units_below = result[i].units_below.join(",");

                result[i].lith = larkin.pipifyAttrs(result[i].lith);
                result[i].environ = larkin.pipifyAttrs(result[i].environ);
                result[i].econ = larkin.pipifyAttrs(result[i].econ);

                result[i].refs = result[i].refs.join("|");
              }
            }

            if (
              req.query.format &&
              api.acceptedFormats.geo[req.query.format] &&
              !cb
            ) {
              var geomAge =
                req.query.geom_age && req.query.geom_age === "top"
                  ? ["t_plng", "t_plat"]
                  : req.query.geom_age === "bottom"
                    ? ["b_plng", "b_plat"]
                    : ["clng", "clat"];

              dbgeo.parse(
                result,
                {
                  geometryType: "ll",
                  geometryColumn: geomAge,
                  outputFormat: larkin.getOutputFormat(req.query.format),
                },
                function (error, output) {
                  if (error) {
                    return larkin.error(
                      req,
                      res,
                      next,
                      "An error was incurred during conversion",
                    );
                  } else {
                    if (
                      larkin.getOutputFormat(req.query.format) === "geojson"
                    ) {
                      output = gp(output, 4);
                    }
                    callback(null, data, output);
                  }
                },
              );
            } else {
              callback(null, data, result);
            }
          }
        });
      },
    ],
    function (error, data, result) {
      if (error) {
        console.log(error);
        if (cb) {
          cb(error);
        } else {
          return larkin.error(req, res, next, "Something went wrong");
        }
      } else {
        if (cb) {
          cb(null, result);
        } else {
          return larkin.sendData(
            req,
            res,
            next,
            {
              format: api.acceptedFormats.standard[req.query.format]
                ? req.query.format
                : "json",
              bare: api.acceptedFormats.bare[req.query.format] ? true : false,
              refs: req.query.response === "long" ? "refs" : false,
            },
            {
              data: result,
            },
          );
        }
      }
    },
  );
};
