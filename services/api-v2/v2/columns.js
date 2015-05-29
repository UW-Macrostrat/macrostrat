var api = require("./api"),
    async = require("async"),
    dbgeo = require("dbgeo"),
    gp = require("geojson-precision"),
    _ = require("underscore"),
    larkin = require("./larkin");

function summarizeLith(data, type, total_units) {
  var lithGroups = _.groupBy(_.flatten(data.map(function(d) { return d[type] })), function(d) {return d.type});
  var liths = []

  Object.keys(lithGroups).forEach(function(d) {
    var props = lithGroups[d].map(function(d) { return d.prop })
    var sum = parseFloat((_.reduce(props, function(a, b) { return a + b }, 0)/total_units).toFixed(4))
    liths.push({"type": d, "prop": sum});
  });

  return liths;
}

function pipifyLiths(data) {
  return data.map(function(d) {
    return d.type + " - " + d.prop;
  }).join("|");
}


module.exports = function(req, res, next) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }

  async.waterfall([
    // First pass the request to the /units route and get the long response
    function(callback) {

      require("./units")(req, null, null, function(result) {
        var cols = _.groupBy(result, function(d) {
          return d.col_id;
        });

        var new_cols = {}
        Object.keys(cols).forEach(function(col_id) {
          
          new_cols[col_id] = {
            "max_thick": _.max(cols[col_id], function(d) { return d.max_thick; }).max_thick,
            "min_thick": _.min(cols[col_id], function(d) { return d.min_thick; }).min_thick,
            "b_age": _.max(cols[col_id], function(d) { return d.b_age; }).b_age,
            "t_age": _.min(cols[col_id], function(d) { return d.t_age; }).t_age,
            "pbdb_collections": _.reduce(cols[col_id].map(function(d) { return d.pbdb_collections }), function(a, b) { return a + b}, 0),
            "environ_class": _.uniq(_.flatten(cols[col_id].filter(function(d) { if (d.environ_class.length > 0) return d; }).map(function(d) { return d.environ_class }))),
            "environ_type": _.uniq(_.flatten(cols[col_id].filter(function(d) { if (d.environ_type.length > 0) return d; }).map(function(d) { return d.environ_type }))),
            "environ": _.uniq(_.flatten(cols[col_id].filter(function(d) { if (d.environ.length > 0) return d; }).map(function(d) { return d.environ }))),
            "lith": summarizeLith(cols[col_id], "lith", result.length),
            "lith_type": summarizeLith(cols[col_id], "lith_type", result.length),
            "lith_class": summarizeLith(cols[col_id], "lith_class", result.length)
          }
        });
        callback(null, new_cols);
      });
    },

    // Using the unique column IDs returned from units, query columns
    function(new_cols, callback) {

      var geo = (req.query.format && api.acceptedFormats.geo[req.query.format]) ? ", AsWKT(col_areas.col_area) AS wkt" : "",
          params = {"col_ids": Object.keys(new_cols)},
          orderby = "";

      if (req.query.lat && req.query.lng && req.query.adjacents) {
        orderby = "ORDER BY ST_Distance(col_areas.col_area, GeomFromText(:point))";
        params["point"] = "POINT(" + req.query.lng + " " + req.query.lat + ")";

      } else if (req.query.col_id && req.query.adjacents) {
        orderby = "ORDER BY ST_Distance(ST_Centroid(col_areas.col_area), (SELECT ST_Centroid(col_area) FROM col_areas WHERE col_id = :col_id))";
        params["col_id"] = req.query.col_id;
      }

      larkin.query("SELECT col_areas.col_id, col_name, col_group, col_groups.id AS col_group_id, col AS group_col_id, round(cols.col_area, 1) AS col_area, project_id" +  geo + " FROM col_areas JOIN cols ON cols.id = col_areas.col_id JOIN col_groups ON col_groups.id = cols.col_group_id WHERE status_code = 'active' AND cols.id IN (:col_ids) GROUP BY col_areas.col_id " + orderby, params, function(error, result) {
        if (error) {
          callback(error);
        } else {
          callback(null, new_cols, result);
        }
      });
    }

  // Once units and columns have been queried, wrap things up and send it
  ], function(error, unit_data, column_data) {
    if (error) {
      return larkin.error(req, res, next, error);
    }
    column_data.forEach(function(d) {
      if (req.query.response === "long") {
        d = _.extend(d, unit_data[d.col_id]);

        if (req.query.format === "csv") {
          d.environ = d.environ.join("|");
          d.environ_type = d.environ_type.join("|");
          d.environ_class = d.environ_class.join("|");
          d.lith = pipifyLiths(d.lith);
          d.lith_type = pipifyLiths(d.lith_type);
          d.lith_class = pipifyLiths(d.lith_class);
        } 
      }  
    });

    if (req.query.format && api.acceptedFormats.geo[req.query.format]) {
      dbgeo.parse({
        "data": column_data,
        "geometryColumn": "wkt",
        "geometryType": "wkt",
        "outputFormat": larkin.getOutputFormat(req.query.format),
        "callback": function(error, output) {
          if (error) {
            larkin.error(req, res, next, "An error was incurred during conversion");
          } else {
            if (larkin.getOutputFormat(req.query.format) === "geojson") {
              output = gp(output, 4);
            }
            if (api.acceptedFormats.bare[req.query.format]) {
              larkin.sendBare(output, res, next);
            } else {
              larkin.sendCompact(output, res, null, next);
            }
          }
        }
      });
    } else {
      larkin.sendData(column_data, res, (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json", next);
    }
  });
}