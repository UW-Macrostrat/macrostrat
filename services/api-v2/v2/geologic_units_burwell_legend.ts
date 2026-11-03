import { cartoFromCompilation } from "./mobile/map-source";

var api = require("./api"),
  async = require("async"),
  larkin = require("./larkin");

const CARTO_SCALES = ["tiny", "small", "medium", "large"];

/* The legend entries `carto` draws at a scale, under `CARTO_BUILD=compilation`:
   every map owning a face in the layer for the scale's first zoom, with its
   whole legend (a mosaic member's within its footprint). API v3's `legend.sql`,
   `all` form. */
function compilationLegendIds(scale) {
  return `
    WITH target AS (
      SELECT
        map_bounds.serving_source(s.id, sb.min_zoom) AS source_id,
        map_bounds.face_layer_for(s.id, sb.min_zoom) AS layer_id
      FROM (SELECT map_bounds.resolve_source('carto') AS id) s
      CROSS JOIN map_bounds.scale_band sb
      WHERE sb.scale = '${scale}'
    ),
    owners AS MATERIALIZED (
      SELECT DISTINCT mf.map_id
      FROM map_bounds_topology.map_face mf
      WHERE mf.map_layer = (SELECT layer_id FROM target)
        AND map_bounds.has_content(mf.map_id)
      UNION ALL
      SELECT t.source_id FROM target t WHERE t.layer_id IS NULL
    ),
    content AS MATERIALIZED (
      SELECT c.source_id, c.footprint, cs.scale
      FROM owners o
      CROSS JOIN LATERAL map_bounds.content_of(o.map_id) c
      JOIN maps.sources cs
        ON cs.source_id = c.source_id
       AND cs.scale = ANY (enum_range(NULL::maps.map_scale)::text[])
    )
    SELECT ml.legend_id
    FROM content c
    JOIN maps.polygons p
      ON p.source_id = c.source_id
     AND p.scale = CAST(c.scale AS maps.map_scale)
     AND ST_Intersects(p.geom, c.footprint)
    JOIN maps.map_legend ml ON ml.map_id = p.map_id
    WHERE c.footprint IS NOT NULL
    UNION
    SELECT l.legend_id
    FROM content c
    JOIN maps.legend l ON l.source_id = c.source_id
    WHERE c.footprint IS NULL
  `;
}

function cartoLegendFilter(scale) {
  if (!CARTO_SCALES.includes(scale)) return "";
  let legendIds = `SELECT legend_id FROM maps.map_legend JOIN carto_new.${scale} USING (map_id)`;
  if (cartoFromCompilation()) legendIds = compilationLegendIds(scale);
  return ` AND m.legend_id IN (${legendIds})`;
}

module.exports = function (req, res, next, cb) {
  if (Object.keys(req.query).length < 1) {
    larkin.info(req, res, next);
  } else {
    var where = [],
      where_lith = [],
      params = [],
      params_lith = [],
      carto_scale = "",
      limit;

    if ("sample" in req.query) {
      limit = " LIMIT 5";
    } else {
      limit = "";
    }

    // Process the parameters
    async.parallel(
      [
        // Lat/lng
        // map_id
        function (callback) {
          if (req.query.map_id && req.query.map_id != "undefined") {
            where.push("m.map_id = ANY($" + (where.length + 1) + ")");
            params.push(larkin.parseMultipleIds(req.query.map_id));
          }

          callback(null);
        },

        // strat_name_id
        function (callback) {
          // Need to go down the hierarchy!
          if (req.query.strat_name_id) {
            req.query.rule = "down";
            require("./definitions/strat_names")(
              req,
              null,
              null,
              function (error, result) {
                if (error || !result) {
                  return callback(null);
                }
                var strat_name_ids = result.map(function (d) {
                  return d.strat_name_id;
                });

                where.push(
                  "m.strat_name_ids && $" + (where.length + 1) + "::int[]",
                );
                params.push(strat_name_ids);
                callback(null);
              },
            );
          } else {
            callback(null);
          }
        },

        // unit_id
        function (callback) {
          if (req.query.unit_id) {
            var unit_ids = larkin.parseMultipleIds(req.query.unit_id);

            where.push("m.unit_ids && $" + (where.length + 1) + "::int[]");
            params.push(unit_ids);
          }

          callback(null);
        },

        // scale
        function (callback) {
          if (req.query.scale) {
            where.push("scale = ANY($" + (where.length + 1) + ")");
            params.push(larkin.parseMultipleStrings(req.query.scale));
          }

          callback(null);
        },

        // comments
        function (callback) {
          if (req.query.comments) {
            where.push("comments ILIKE $" + (where.length + 1));
            params.push("%" + req.query.comments + "%");
          }

          callback(null);
        },

        // descrip
        function (callback) {
          if (req.query.description) {
            where.push("descrip ILIKE $" + (where.length + 1));
            params.push("%" + req.query.description + "%");
          }

          callback(null);
        },

        // source_id
        function (callback) {
          if (req.query.source_id) {
            where.push("m.source_id = ANY($" + (where.length + 1) + ")");
            params.push(larkin.parseMultipleIds(req.query.source_id));
          }

          callback(null);
        },

        // lith_id
        function (callback) {
          if (req.query.lith_id) {
            var lith_ids = larkin.parseMultipleIds(req.query.lith_id);

            where_lith.push(
              "m.lith_ids && $" +
                (where_lith.length + 1 + where.length) +
                "::int[]",
            );
            params_lith.push(lith_ids);
          }

          callback(null);
        },

        // lith_type
        function (callback) {
          if (req.query.lith_type) {
            var lith_type = larkin.parseMultipleStrings(req.query.lith_type);

            where_lith.push(
              "m.lith_types && $" + (where_lith.length + 1 + where.length) + "",
            );
            params_lith.push(lith_type);
          }

          callback(null);
        },

        // lith_classes
        function (callback) {
          if (req.query.lith_class) {
            var lith_class = larkin.parseMultipleStrings(req.query.lith_class);

            where_lith.push(
              "m.lith_classes && $" +
                (where_lith.length + 1 + where.length) +
                "",
            );
            params_lith.push(lith_class);
          }

          callback(null);
        },

        // lith_classes
        function (callback) {
          if (req.query.carto) {
            carto_scale = cartoLegendFilter(req.query.carto);
          }

          callback(null);
        },
      ],
      function () {
        // If no valid parameters passed, return an Error
        if (
          where.length < 1 &&
          where_lith.length < 1 &&
          !("sample" in req.query) &&
          !req.query.carto
        ) {
          if (cb) return cb("No valid parameters passed");
          return larkin.error(req, res, next, "No valid parameters passed");
        }

        var where_start = " WHERE sources.status_code='active'";
        if (where.length > 0) {
          where = " AND " + where.join(" AND ");
        } else {
          where = "";
        }

        if (where_lith.length > 0) {
          where_lith = " AND (" + where_lith.join(" OR ") + ")";
        } else {
          where_lith = "";
        }

        var where_combined = "";
        if (where_lith.length > 0 && where.length > 0) {
          where_combined = where.concat(where_lith);
          where = "";
          where_lith = "";
        }

        var params_combined = params.concat(params_lith);

        var sql =
          "SELECT legend_id, m.source_id, sources.scale, to_json(regexp_replace(m.name, E'[\\n\\r\\f\\u000B\\u0085\\u2028\\u2029]+', ' ', 'g')) as map_unit_name, to_json(regexp_replace(strat_name, E'[\\n\\r\\f\\u000B\\u0085\\u2028\\u2029]+', ' ', 'g')) as strat_name,age,to_json(regexp_replace(lith, E'[\\n\\r\\f\\u000B\\u0085\\u2028\\u2029]+', ' ', 'g')) AS lith,to_json(regexp_replace(descrip, E'[\\n\\r\\f\\u000B\\u0085\\u2028\\u2029]+', ' ', 'g')) AS descrip, to_json(regexp_replace(comments, E'[\\n\\r\\f\\u000B\\u0085\\u2028\\u2029]+', ' ', 'g')) AS comments,best_age_top::float t_age,best_age_bottom::float b_age,b_interval,t_interval,strat_name_ids strat_name_id,unit_ids unit_id, lith_classes,lith_types,lith_ids lith_id ,color,m.area::float,tiny_area::float,small_area::float,medium_area::float,large_area::float";

        sql +=
          " FROM maps.legend m JOIN maps.sources USING (source_id)" +
          where_start +
          carto_scale +
          where +
          where_combined +
          where_lith +
          limit;

        //      var scaleSQL = buildSQL(req, where, limit);

        //      var toRun = "SELECT * FROM ( " + scaleSQL + ") doit";

        larkin.queryPg(
          "burwell",
          sql,
          params_combined,
          function (error, result) {
            if (error) {
              if (cb) return cb(error);
              larkin.error(req, res, next, error);
            } else {
              if (
                req.query.format &&
                api.acceptedFormats.geo[req.query.format]
              ) {
                dbgeo.parse(
                  result.rows,
                  {
                    geometryType: "geojson",
                    geometryColumn: "geometry",
                    outputFormat: larkin.getOutputFormat(req.query.format),
                  },
                  function (error, result) {
                    if (error) {
                      if (cb) return cb(error);
                      larkin.error(req, res, next, error);
                    } else {
                      if (
                        larkin.getOutputFormat(req.query.format) === "geojson"
                      ) {
                        result = gp(result, 5);
                      }
                      if (cb) return cb(null, result);
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
                          refs: "source_id",
                        },
                        {
                          data: result,
                        },
                      );
                    }
                  },
                );
              } else {
                if (cb) return cb(null, result.rows);
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
                    refs: "source_id",
                  },
                  {
                    data: result.rows,
                  },
                );
              }
            }
          },
        );
      },
    );
  }
};
