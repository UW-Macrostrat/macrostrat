var api = require("../api"),
  async = require("async"),
  larkin = require("../larkin"),
  _ = require("underscore");

function buildSQL(req, scale, where, limit) {
  return (
    `(SELECT
    COALESCE(mm.unit_ids, '{}') AS macro_units,
    COALESCE(mm.strat_name_ids, '{}') AS strat_names
    FROM maps.${scale} m
    JOIN lookup_${scale} mm ON m.map_id = mm.map_id ` +
    where +
    limit +
    ")"
  );
}

function buildStratNameSQL(scale, where, limit) {
  return (
    `(SELECT
    s.scale, unnest(mm.strat_name_ids) strat_name_id
    FROM maps.${scale} m
    JOIN lookup_${scale} mm ON m.map_id = mm.map_id
    JOIN maps.sources s ON s.source_id = m.source_id
    ` +
    where +
    ` AND array_length(strat_name_ids, 1) > 0)`
  );
}

var nextRank = {
  fm: "gp",
  gp: "sgp",
};
var fullRank = {
  fm: "Formation",
  gp: "Group",
  sgp: "Supergroup",
};

function parseBest(names, rank, callback) {
  var grouped = _.groupBy(names, function (d) {
    return d[rank];
  });

  var best = [];
  Object.keys(grouped).forEach(function (d) {
    if (d === "") {
      grouped[d].forEach(function (j) {
        best.push(j.strat_name_long);
      });
    } else {
      best.push(d + " " + fullRank[rank]);
    }
  });
  callback(best);
}
function groupStratNames(names, rank, callback) {
  if (!rank) {
    rank = "fm";
  }
  parseBest(names, rank, function (result) {
    if (result.length > 3 && rank != "sgp") {
      groupStratNames(names, nextRank[rank], callback);
    } else if (rank === "sgp" && result.length > 3) {
      parseBest(names, "gp", function (bestNames) {
        callback(bestNames);
      });
    } else {
      callback(result);
    }
  });
}

function summarizeBurwell(lat, lng, callback) {
  require("../geologic_units_burwell")(
    { query: { lat: lat, lng: lng } },
    null,
    null,
    function (error, result) {
      if (error) return callback(error);
      if (result.length) {
        var bestAge = _.min(result, function (d) {
          return d.b_int_age - d.t_int_age;
        });
        var parsed = {
          b_age: bestAge.b_int_age,
          t_age: bestAge.t_int_age,
          b_int_name: bestAge.b_int_name,
          t_int_name: bestAge.t_int_name,
          lith: _.countBy(
            _.uniq(
              _.flatten(
                result.map(function (d) {
                  return d.liths;
                }),
              ),
            ),
          ),
        };

        if (Object.keys(parsed.lith).length) {
          require("../definitions/lithologies")(
            {
              query: {
                lith_id: Object.keys(parsed.lith).join(","),
              },
            },
            null,
            null,
            function (error, result) {
              var totalLiths = Object.keys(parsed.lith)
                .map(function (d) {
                  return parsed.lith[d];
                })
                .reduce(function (a, b) {
                  return a + b;
                }, 0);

              result.forEach(function (d) {
                d.prop = totalLiths / parsed.lith[d.lith_id];
                delete d.t_units;
              });

              parsed.lith = result;
              callback(null, parsed);
            },
          );
        } else {
          result.lith = [];
          callback(null, parsed);
        }
      } else {
        callback(null, {});
      }
    },
  );
}

module.exports = function (req, res, next) {
  if (Object.keys(req.query).length < 1) {
    larkin.info(req, res, next);
  } else {
    async.waterfall(
      [
        function (callback) {
          var where = [],
            params = [],
            limit;

          if ("sample" in req.query) {
            limit = " LIMIT 5";
            req.query.scale = "medium";
          } else {
            limit = "";
          }

          if (req.query.lat && req.query.lng) {
            req.query.lng = larkin.normalizeLng(req.query.lng);
            if (req.query.buffer && req.query.buffer <= 50) {
              where.push(
                "ST_Intersects(m.geom, ST_Buffer(ST_GeographyFromText($" +
                  (where.length + 1) +
                  "), $" +
                  (where.length + 2) +
                  ")::geometry)",
              );
              params.push(
                "POINT(" + req.query.lng + " " + req.query.lat + ")",
                req.query.buffer * 1000,
              );
            } else {
              where.push(
                "ST_Intersects(m.geom, ST_GeomFromText($" +
                  (where.length + 1) +
                  ", 4326))",
              );
              params.push("POINT(" + req.query.lng + " " + req.query.lat + ")");
            }
          }

          // If no valid parameters passed, return an Error
          if (where.length < 1 && !("sample" in req.query)) {
            return larkin.error(req, res, next, "No valid parameters passed");
          }

          if (where.length > 0) {
            where = " WHERE " + where.join(" AND ");
          } else {
            where = "";
          }

          var scaleSQL = ["tiny", "small", "medium", "large"]
            .map(function (d) {
              return buildSQL(req, d, where, limit);
            })
            .join(" UNION ");

          var toRun =
            "WITH first AS (SELECT unnest(macro_units) units FROM ( " +
            scaleSQL +
            ") doit) SELECT array_agg(distinct units) units FROM first";

          larkin.queryPg("burwell", toRun, params, function (error, result) {
            if (error) {
              return callback(error);
            }

            callback(null, result.rows);
          });
        },

        function (units, callback) {
          if (!units.length || !units[0].units) {
            summarizeBurwell(
              req.query.lat,
              req.query.lng,
              function (error, data) {
                if (error) return callback(error);
                return callback(null, data);
              },
            );
          } else {
            require("../units")(
              { query: { unit_id: units[0].units } },
              null,
              null,
              function (error, result) {
                if (error) return callback(error);

                if (!result.length) return callback(null, {});

                callback(null, {
                  max_thick: _.reduce(
                    result.map(function (d) {
                      return d.max_thick;
                    }),
                    function (a, b) {
                      return a + b;
                    },
                    0,
                  ),
                  max_thick: _.reduce(
                    result.map(function (d) {
                      if (d.min_thick === 0) {
                        return d.max_thick;
                      } else {
                        return d.min_thick;
                      }
                    }),
                    function (a, b) {
                      return a + b;
                    },
                    0,
                  ),
                  min_min_thick: _.reduce(
                    result.map(function (d) {
                      return d.min_thick;
                    }),
                    function (a, b) {
                      return a + b;
                    },
                    0,
                  ),
                  b_age: _.max(result, function (d) {
                    return d.b_age;
                  }).b_age,
                  t_age: _.min(result, function (d) {
                    return d.t_age;
                  }).t_age,
                  b_int_name: _.max(result, function (d) {
                    return d.b_age;
                  }).b_int_name,
                  t_int_name: _.min(result, function (d) {
                    return d.t_age;
                  }).t_int_name,
                  lith: larkin.summarizeAttribute(result, "lith"),
                  environ: larkin.summarizeAttribute(result, "environ"),
                  econs: larkin.summarizeAttribute(result, "econ"),
                });
              },
            );
          }
        },

        function (unit_summary, callback) {
          // Basically indicates units were returned
          if (unit_summary.hasOwnProperty("max_thick")) {
            // Get best strat names
            var where = [],
              params = [],
              limit = "";

            if (req.query.lat && req.query.lng) {
              req.query.lng = larkin.normalizeLng(req.query.lng);
              where.push(
                "ST_Intersects(m.geom, ST_GeomFromText($" +
                  (where.length + 1) +
                  ", 4326))",
              );
              params.push("POINT(" + req.query.lng + " " + req.query.lat + ")");
            }

            if (where.length > 0) {
              where = " WHERE " + where.join(" AND ");
            } else {
              where = "";
            }

            var scaleSQL = ["tiny", "small", "medium", "large"]
              .map(function (d) {
                return buildStratNameSQL(d, where, limit);
              })
              .join(" UNION ");

            var toRun =
              "WITH first AS ( " +
              scaleSQL +
              " ) SELECT scale, array_agg(distinct strat_name_id) strat_name_ids FROM first GROUP BY scale";

            larkin.queryPg("burwell", toRun, params, function (error, result) {
              if (error) {
                return callback(error);
              }
              var scales = result.rows.map(function (d) {
                return d.scale;
              });

              var bestScale = "";
              switch (true) {
                case scales.indexOf("large") > -1:
                  bestScale = "large";
                  break;
                case scales.indexOf("medium") > -1:
                  bestScale = "medium";
                  break;
                case scales.indexOf("small") > -1:
                  bestScale = "small";
                  break;
                case scales.indexOf("tiny") > -1:
                  bestScale = "tiny";
                  break;
              }

              var bestNames = result.rows
                .filter(function (d) {
                  if (d.scale === bestScale) return d;
                })
                .map(function (d) {
                  return d.strat_name_ids;
                })[0];

              require("../definitions/strat_names")(
                { query: { strat_name_id: bestNames.join(",") } },
                null,
                null,
                function (error, result) {
                  if (error) return callback(error);

                  if (result.length <= 3) {
                    unit_summary.strat_names = result.map(function (d) {
                      return d.strat_name_long;
                    });
                    unit_summary.strat_name_ids = result.map(function (d) {
                      return d.strat_name_id;
                    });
                    callback(null, unit_summary);
                  } else {
                    groupStratNames(result, null, function (names) {
                      unit_summary.strat_names = names;
                      callback(null, unit_summary);
                    });
                  }
                },
              );
            });
          } else {
            // No units, thus no strat names so carry on
            callback(null, unit_summary);
          }
        },

        function (unit_summary, callback) {
          require("../elevation")(req, null, null, function (error, result) {
            if (result && result.length) {
              unit_summary["elevation"] = result[0].elevation;
            }
            callback(null, unit_summary);
          });
        },

        // Produce a warning message if on public lands
        function (unit_summary, callback) {
          larkin.queryPg(
            "rockd",
            `
        SELECT CASE
          WHEN type LIKE '%NPS%'
            THEN CONCAT('You are in ', name, ' which is managed by the National Park Service. Removal of natural objects is strictly prohibited.')
          WHEN type = 'state_park'
            THEN CONCAT('You are in ', name, ' which is a locally managed protected area. Please check local laws before removing or collecting any natural objects.')
          WHEN type NOT LIKE '%NPS%'
            THEN CONCAT('You are in ', name, ' which is federal land. Removal of natural objects is regulated by state and federal laws and regulations.')
          ELSE
            ''
          END AS message,
          COALESCE(url, '') url
        FROM places
        WHERE ST_Intersects(geom, $1)
        AND type != 'incorp'
        LIMIT 1
        `,
            [
              "SRID=4326;POINT(" +
                larkin.normalizeLng(req.query.lng) +
                " " +
                req.query.lat +
                ")",
            ],
            function (error, data) {
              if (data && data.rows && data.rows.length) {
                unit_summary["warning"] = data.rows[0];
              }
              callback(null, unit_summary);
            },
          );
        },
        //TODO move places table to macrostrat API
        function (unit_summary, callback) {
          larkin.queryPg(
            "rockd",
            "SELECT CONCAT(name, ', ', state) AS place FROM public.places ORDER BY geom <#> $1 LIMIT 1",
            [
              "SRID=4326;POINT(" +
                larkin.normalizeLng(req.query.lng) +
                " " +
                req.query.lat +
                ")",
            ],
            function (error, data) {
              if (data && data.rows && data.rows.length) {
                unit_summary["near"] = data.rows[0].place;
              }
              callback(null, unit_summary);
            },
          );
        },

        function (unit_summary, callback) {
          if (!unit_summary.b_age) return callback(null, unit_summary);

          require("../definitions/intervals")(
            {
              query: {
                t_age: unit_summary.t_age,
                b_age: unit_summary.b_age,
                timescale_id: "3,11",
              },
            },
            null,
            null,
            function (error, result) {
              if (error) return callback(error);

              if (result.length) {
                var best = result.filter(function (d) {
                  var timescales = d.timescales.map(function (j) {
                    return j.timescale_id;
                  });
                  if (timescales.indexOf(3) > -1) {
                    return d;
                  }
                });
                var nextBest = result.filter(function (d) {
                  var timescales = d.timescales.map(function (j) {
                    return j.timescale_id;
                  });
                  if (timescales.indexOf(11) > -1 && d.int_type === "era") {
                    return d;
                  }
                });
                unit_summary["c_int_name"] = best.length
                  ? best[0].name
                  : nextBest.length
                    ? nextBest[0].name
                    : "";
                unit_summary["int_color"] = best.length
                  ? best[0].color
                  : nextBest.length
                    ? nextBest[0].color
                    : "";
                // unit_summary['c_int_name'] = result[0].name;
                // unit_summary['int_color'] = result[0].color;
              } else {
                require("../definitions/intervals")(
                  {
                    query: {
                      name: unit_summary.b_int_name,
                    },
                  },
                  null,
                  null,
                  function (error, result) {
                    if (error) return callback(error);
                    if (!result || !result.length)
                      return callback(null, unit_summary);

                    unit_summary["int_color"] = result[0].color;
                  },
                );
              }
              callback(null, unit_summary);
            },
          );
        },

        function (unit_summary, callback) {
          if (!unit_summary.lith || !unit_summary.lith.length)
            return callback(null, unit_summary);

          require("../definitions/lithologies")(
            {
              query: {
                lith_id: _.max(unit_summary.lith, function (d) {
                  return d.prop;
                }).lith_id.toString(),
              },
            },
            null,
            null,
            function (error, result) {
              if (error) return callback(error);

              if (result) {
                unit_summary["lith_color"] = result[0].color;
              }

              callback(null, unit_summary);
            },
          );
        },

        function (unit_summary, callback) {
          larkin.queryPg(
            "burwell",
            `
          SELECT sub.boundary_id, sub.name, sub.boundary_group, sub.boundary_type, sub.boundary_class, sub.descrip, sub.wiki_link,
          row_to_json(
            (SELECT x FROM (SELECT sources.source_id, sources.name, sources.url, sources.ref_title, sources.authors, sources.ref_year, sources.ref_source, COALESCE(sources.isbn_doi, '') AS isbn_doi) x)
         ) AS ref
          FROM
              (
              SELECT
                  boundary_id,
                  source_id,
                  COALESCE(name, '') AS name,
                  COALESCE(boundary_group, '') AS boundary_group,
                  COALESCE(boundary_type, '') AS boundary_type,
                  COALESCE(initcap(boundary_class), '') AS boundary_class,
                  COALESCE(descrip, '') AS descrip,
                  COALESCE(wiki_link, '') AS wiki_link,
                  row_number() OVER(PARTITION BY boundary_class ORDER BY ST_Area(geom) ASC) as rn
              FROM geologic_boundaries.boundaries
              WHERE ST_Intersects(geom, $1)
              ) sub
          JOIN geologic_boundaries.sources ON sub.source_id = sources.source_id
          WHERE rn = 1
        `,
            [`SRID=4326;POINT(${req.query.lng} ${req.query.lat})`],
            function (error, result) {
              if (result && result.rows && result.rows.length) {
                unit_summary["regions"] = result.rows;
              } else {
                unit_summary["regions"] = [];
              }
              callback(null, unit_summary);
            },
          );
        },
      ],
      function (error, result) {
        if (error) {
          larkin.trace("ERROR - ", error);
          larkin.error(req, res, next, error);
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
              data: result,
            },
          );
        }
      },
    );
  }
};
