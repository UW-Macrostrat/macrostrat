var api = require("./api"),
  async = require("async"),
  wellknown = require("wellknown"),
  gp = require("geojson-precision"),
  buffer = require("turf-buffer"),
  area = require("turf-area"),
  dbgeo = require("dbgeo"),
  larkin = require("./larkin");

module.exports = function (req, res, next) {
  if (Object.keys(req.query).length < 1) {
    larkin.info(req, res, next);
  } else {
    var geo =
      req.query.format && api.acceptedFormats.geo[req.query.format]
        ? true
        : false;

    var where = [],
      params = [],
      limit = "sample" in req.query ? " LIMIT 5" : "",
      from =
        "gmus.lookup_units lu JOIN gmus.ages a ON lu.unit_link = a.unit_link LEFT JOIN gmus.liths l ON lu.unit_link = l.unit_link LEFT JOIN gmus.best_geounits_macrounits gm ON lu.gid = gm.geologic_unit_gid",
      geomQuery = geo ? ", ST_AsGeoJSON(geom) AS geometry" : "",
      orderBy = "";

    async.parallel(
      [
        function (callback) {
          if (req.query.lat && req.query.lng) {
            if (req.query.adjacents === "true") {
              where.push(
                "gid = ANY (SELECT unnest(array_append(touches, (SELECT gid FROM gmus.lookup_units WHERE ST_Contains(geom, ST_GeomFromText($" +
                  where.length +
                  1 +
                  ", 4326))))) FROM gmus.adjacents WHERE geologic_unit_gid = (SELECT gid FROM gmus.lookup_units WHERE ST_Contains(geom, ST_GeomFromText($" +
                  where.length +
                  1 +
                  ", 4326))))",
              );
              params.push(
                "POINT(" +
                  larkin.normalizeLng(req.query.lng) +
                  " " +
                  req.query.lat +
                  ")",
              );
              orderBy +=
                " )a ORDER BY ST_Distance(geom, ST_GeomFromText($" +
                where.length +
                ", 4326))";
            } else {
              where.push(
                " ST_Contains(geom, ST_GeomFromText($" +
                  (where.length + 1) +
                  ", 4326))",
              );
              params.push(
                "POINT(" +
                  larkin.normalizeLng(req.query.lng) +
                  " " +
                  req.query.lat +
                  ")",
              );
            }
          }
          callback(null);
        },

        function (callback) {
          if (req.query.gid && req.query.gid != "undefined") {
            if (req.query.adjacents === "true") {
              where.push(
                "gid = $" +
                  (where.length + 1) +
                  " OR gid = ANY (SELECT unnest(touches) from gmus.adjacents where geologic_unit_gid = $" +
                  (where.length + 1) +
                  ")",
              );
              params.push(req.query.gid);
            } else {
              where.push("gid = $" + (where.length + 1));
              params.push(req.query.gid);
            }
          }

          callback(null);
        },

        function (callback) {
          // Need to go down the hierarchy!
          if (req.query.strat_name_id) {
            req.query.rule = "down";
            require("./definitions/strat_names")(
              req,
              null,
              null,
              function (error, result) {
                var strat_name_ids = result.map(function (d) {
                  return d.strat_name_id;
                });

                where.push(
                  "gm.best_names && $" + (where.length + 1) + "::int[]",
                );
                params.push(strat_name_ids);
                callback(null);
              },
            );
          } else {
            callback(null);
          }
        },

        function (callback) {
          if (req.query.unit_id) {
            var unit_ids = larkin.parseMultipleIds(req.query.unit_id);

            where.push("gm.best_units && $" + (where.length + 1) + "::int[]");
            params.push(unit_ids);
          }

          callback(null);
        },

        function (callback) {
          if (req.query.search) {
            where.push(
              "text_search @@ plainto_tsquery('macro', $" +
                (where.length + 1) +
                ")",
            );
            params.push(req.query.search);
          }

          callback(null);
        },

        function (callback) {
          if (req.query.interval_name) {
            where.push(
              "macro_b_age <= (SELECT age_bottom FROM macrostrat.intervals WHERE interval_name = $" +
                (where.length + 1) +
                ") AND macro_t_age >= (SELECT age_top FROM macrostrat.intervals WHERE interval_name = $" +
                (where.length + 2) +
                ")",
            );
            params.push(req.query.interval_name, req.query.interval_name);
          }

          callback(null);
        },

        function (callback) {
          if (req.query.unit_link) {
            where.push(" lu.unit_link = $" + (where.length + 1));
            params.push(req.query.unit_link);
          }

          callback(null);
        },

        function (callback) {
          if (req.query.shape) {
            var bufferSize =
              req.query.buffer && !isNaN(parseInt(req.query.buffer))
                ? parseInt(req.query.buffer) * 1000
                : 1;

            // Convert shape + buffer to geojson
            var geojson = wellknown(decodeURI(req.query.shape)),
              bufferedGeojson = buffer(geojson, bufferSize, "kilometers"),
              totalArea = area(bufferedGeojson) * 0.000001;

            // Test area
            if (totalArea > 1000000000) {
              return larkin.error(
                req,
                res,
                next,
                "Area too large. Please select a smaller area.",
              );
            }

            from =
              "subset lu JOIN gmus.ages a ON lu.unit_link = a.unit_link LEFT JOIN gmus.liths l ON lu.unit_link = l.unit_link LEFT JOIN gmus.best_geounits_macrounits gm ON lu.gid = gm.geologic_unit_gid, linestring";
            where.push("ST_Intersects(geom, buffer) is true");
            geomQuery = geo
              ? ", ST_AsGeoJSON(ST_Intersection(ST_Buffer(geom, 0)::geography, buffer)) AS geometry"
              : "";
            params.push(req.query.shape, bufferSize);
          }
          callback(null);
        },
      ],
      function () {
        if (where.length < 1 && !("sample" in req.query)) {
          return larkin.error(req, res, next, "Invalid params");
        }

        if (where.length > 0) {
          where = " WHERE " + where.join(", ");
        }

        // Some things if querying by lat/lng
        var sql =
          orderBy.length > 0
            ? "SELECT gid, area, unit_link, lithology, rocktype, macro_units, t_int_id, t_age, b_int_id, b_age, containing_interval, interval_color, unit_com, unit_name, unitdesc, strat_unit" +
              (geo ? ", geometry" : "") +
              " FROM ("
            : "";

        if (req.query.shape) {
          sql +=
            "WITH linestring AS (SELECT ST_Buffer((ST_Segmentize($" +
            (params.length - 1) +
            "::geography, 100000)::geometry)::geography, $" +
            params.length +
            ")::geometry AS buffer), states AS (SELECT postal FROM us_states WHERE ST_Intersects(geom::geography, (SELECT buffer FROM linestring))), subset AS (SELECT * FROM gmus.lookup_units WHERE upper(state) in (SELECT postal FROM states))";
        }

        sql +=
          "SELECT DISTINCT ON (gid) gid, lu.area_km2::int AS area, lu.unit_link, macro_color AS interval_color, (SELECT array_agg(liths) FROM unnest(array[lith1, lith2, lith3, lith4, lith5]) liths WHERE liths IS NOT null) AS lithology, (SELECT array_agg(DISTINCT rocktypes) FROM unnest(array[rocktype1, rocktype2, u_rocktype1, u_rocktype2, u_rocktype3]) rocktypes WHERE rocktypes IS NOT null) AS rocktype, COALESCE(gm.best_units, '{}') AS macro_units, COALESCE(gm.best_names, '{}') AS strat_names, lu.min_interval_name AS t_int_id, lu.age_top::float AS t_age, lu.max_interval_name as b_int_id, lu.age_bottom::float AS b_age, lu.containing_interval_name AS containing_interval, unit_com, unit_name, unitdesc, COALESCE(strat_unit, '') AS strat_unit, macro_color AS color" +
          (orderBy.length > 0 ? ", geom" : "") +
          geomQuery +
          " FROM " +
          from +
          where +
          orderBy +
          limit;

        larkin.queryPg("geomacro", sql, params, function (error, result) {
          if (error) {
            larkin.error(req, res, next, error);
          } else {
            if (geo) {
              dbgeo.parse(
                result.rows,
                {
                  geometryType: "geojson",
                  geometryColumn: "geometry",
                  outputFormat: larkin.getOutputFormat(req.query.format),
                },
                function (error, result) {
                  if (error) {
                    larkin.error(req, res, next, error);
                  } else {
                    if (
                      larkin.getOutputFormat(req.query.format) === "geojson"
                    ) {
                      result = gp(result, 5);
                    }
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
                  bare: api.acceptedFormats.bare[req.query.format]
                    ? true
                    : false,
                },
                {
                  data: result.rows,
                },
              );
            }
          }
        });
      },
    );
  }
};
