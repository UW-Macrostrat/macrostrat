var api = require("./api"),
    async = require("async"),
    dbgeo = require("dbgeo"),
    gp = require("geojson-precision"),
    _ = require("underscore"),
    larkin = require("./larkin");


module.exports = function(req, res, next) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }

  async.waterfall([
    // First pass the request to the /units route and get the long response
    function(callback) {
      if ("all" in req.query) {
        larkin.cache.fetch("unitSummary", function(data) {
          callback(null, data);
        });
      } else {
        callback(null, null);
      }
    },

    function(data, callback) {
      if (data) {
        return callback(null, data);
      }

      require("./units")(req, null, null, function(error, result) {
        if (error) {
          callback(error);
        }
        if (!result || !result.length) {
          return callback(null, null);
        }
        var cols = _.groupBy(result, function(d) {
          return d.col_id;
        });
        var new_cols = {}
        Object.keys(cols).forEach(function(col_id) {
          new_cols[col_id] = {
            "max_thick": _.reduce(cols[col_id].map(function(d) { return d.max_thick}) , function(a, b) { return a + b}, 0),
            "max_min_thick": _.reduce(cols[col_id].map(function(d) {
              if (d.min_thick === 0) {
                return d.max_thick;
              } else {
                return d.min_thick
              }
            }) , function(a, b) { return a + b}, 0),
            "min_min_thick": _.reduce(cols[col_id].map(function(d) { return d.min_thick}) , function(a, b) { return a + b}, 0),

            "b_age": _.max(cols[col_id], function(d) { return d.b_age; }).b_age,
            "t_age": _.min(cols[col_id], function(d) { return d.t_age; }).t_age,
            "b_int_name": _.max(cols[col_id], function(d) { return d.b_age; }).b_int_name,
            "t_int_name": _.min(cols[col_id], function(d) { return d.t_age; }).t_int_name,

            "pbdb_collections": _.reduce(cols[col_id].map(function(d) { return d.pbdb_collections }), function(a, b) { return a + b}, 0),

            "lith": larkin.summarizeAttribute(cols[col_id], "lith"),
            "environ": larkin.summarizeAttribute(cols[col_id], "environ"),
            "econ": larkin.summarizeAttribute(cols[col_id], "econ"),

            "t_units": cols[col_id].length,
            "t_sections": _.uniq(cols[col_id].map(function(d) { return d.section_id })).length
          }
        });

        callback(null, new_cols);
      });
    },

    function(new_cols, callback) {
      if (!(new_cols)) {
        return callback(null, null, []);
      }

      if ("all" in req.query) {
        if (req.query.format && api.acceptedFormats.geo[req.query.format]) {
          larkin.cache.fetch("columnsGeom", function(data) {
            callback(null, new_cols, data);
          });
        } else {
          larkin.cache.fetch("columnsNoGeom", function(data) {
            callback(null, new_cols, data);
          });
        }
      } else {
        callback(null, new_cols, null);
      }
    },

    // Using the unique column IDs returned from units, query columns
    function(new_cols, data, callback) {
      if (!(new_cols)) {
        return callback(null, null, []);
      }

      if (data) {
        return callback(null, new_cols, data);
      }

      var geo = "";
      var params = [Object.keys(new_cols).map(function(d) { return parseInt(d) })];
      var limit = ("sample" in req.query) ? " LIMIT 5" : "";
      var groupBy = "";
      var orderby = "";

      if (req.query.format && api.acceptedFormats.geo[req.query.format]) {
        if (req.query.shape) {
          geo = ", ST_AsGeoJSON(ST_Intersection(col_areas.col_area, $2)) geojson";
          params.push(req.query.shape);
        } else {
          geo = ", ST_AsGeoJSON(col_areas.col_area) geojson";
        }
        groupBy = ", col_areas.col_area";
      }

      if (req.query.lat && req.query.lng && req.query.adjacents) {
        orderby = "ORDER BY ST_Distance(ST_SetSRID(col_areas.col_area, 4326), ST_GeometryFromText($2, 4326))";
        params.push("POINT(" + larkin.normalizeLng(req.query.lng) + " " + req.query.lat + ")");
        groupBy = ", col_areas.col_area";

      } else if (req.query.col_id && req.query.adjacents) {
        orderby = "ORDER BY ST_Distance(ST_Centroid(col_areas.col_area), (SELECT ST_Centroid(col_area) FROM col_areas WHERE col_id = $2))";
        params.push(req.query.col_id);
      }

      larkin.queryPg("burwell", `
      SELECT
        cols.id AS col_id,
        col_name,
        col_group,
        col_groups.id AS col_group_id,
        col AS group_col_id,
        round(cols.col_area, 1) AS col_area,
        project_id,
        string_agg(col_refs.ref_id::varchar, '|') AS refs
        ${geo}
      FROM macrostrat.cols
      LEFT JOIN macrostrat.col_areas on col_areas.col_id = cols.id
      LEFT JOIN macrostrat.col_groups ON col_groups.id = cols.col_group_id
      LEFT JOIN macrostrat.col_refs ON cols.id = col_refs.col_id
      WHERE status_code = 'active'
        AND col_areas.col_area IS NOT NULL AND cols.id = ANY($1)
      GROUP BY col_areas.col_id, cols.id, col_groups.col_group, col_groups.id ${groupBy}
      ${orderby}
      ${limit}
      `, params, function(error, result) {
        if (error) return callback(error);

        callback(null, new_cols, result.rows);
      });
    }

  // Once units and columns have been queried, wrap things up and send it
  ], function(error, unit_data, column_data) {
    if (error) {
      console.log(error);
      return larkin.error(req, res, next, error);
    }

    if (column_data) {
      column_data.forEach(function(d) {
        if (typeof d.refs === "string" || d.refs instanceof String) {
          d.refs = larkin.jsonifyPipes(d.refs, "integers");
        }

        if (req.query.response === "long") {
          d = _.extend(d, unit_data[d.col_id]);

          if (req.query.format === "csv") {
            d.lith = larkin.pipifyAttrs(d.lith);
            d.environ = larkin.pipifyAttrs(d.environ);
            d.econ = larkin.pipifyAttrs(d.econ);
          }
        }
      });
    }

    if (req.query.format && api.acceptedFormats.geo[req.query.format]) {
      dbgeo.parse({
        "data": column_data || [],
        "geometryColumn": "geojson",
        "geometryType": "geojson",
        "outputFormat": larkin.getOutputFormat(req.query.format)
      }, function(error, output) {
          if (error) {
            larkin.error(req, res, next, "An error was incurred during conversion");
          } else {
            if (larkin.getOutputFormat(req.query.format) === "geojson") {
              output = gp(output, 4);
            }

            larkin.sendData(req, res, next, {
              format: (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json",
              bare: (api.acceptedFormats.bare[req.query.format]) ? true : false,
              compact: true,
              refs: "refs"
            }, {
              data: output
            });

          }
        }
      );
    } else {
      larkin.sendData(req, res, next, {
        format: (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json",
        compact: true,
        refs: "refs"
      }, {
        data: column_data
      });
    }
  });
}
