var api = require("./api"),
    dbgeo = require("dbgeo"),
    gp = require("geojson-precision"),
    larkin = require("./larkin");

module.exports = function(req, res, next) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }
  if (!req.query.line || !req.query.type) {
    return larkin.error(req, res, next, "A valid WKT line and geometry type are required");
  }

  var type = (["gmna", "gmus"].indexOf(req.query.type) > -1) ? req.query.type : "gmna",
      buffer = (req.query.buffer && !isNaN(parseInt(req.query.buffer))) ? parseInt(req.query.buffer)*1000 : 35000

  if (type === "gmna") {
    larkin.queryPg("earthbase", "WITH linestring AS (SELECT ST_Buffer($1::geography, $2) AS buffer) SELECT objectid AS id, unit_abbre, rocktype, lithology AS lith, min_age, max_age, interval_color AS color, ST_AsGeoJSON(ST_Intersection(the_geom, (SELECT buffer FROM linestring))) AS geometry FROM gmna.gmna_for_maps WHERE ST_Intersects(the_geom, (SELECT buffer FROM linestring)) is true", [req.query.line, buffer], function(error, result) {
      if (error) {
        larkin.error(req, res, next, "Something went wrong");
      } else {
        dbgeo.parse({
          "data": result.rows,
          "outputFormat": larkin.getOutputFormat(req.query.format),
          "callback": function(error, result) {
            if (error) {
              larkin.error(req, res, next, "Something went wrong");
            } else {
              if (larkin.getOutputFormat(req.query.format) === "geojson") {
                result = gp(result, 4);
              }
              if (api.acceptedFormats.bare[req.query.format]) {
                larkin.sendBare(result, res, next);
              } else {
                larkin.sendData(result, res, null, next);
              }
            }
          }
        });
      }
    });
  } else {
    larkin.queryPg("earthbase", "WITH linestring AS (SELECT ST_Buffer($1::geography, $2) AS buffer), states as (SELECT postal FROM us_states WHERE ST_Intersects(geom::geography, (SELECT buffer FROM linestring))), subset as (SELECT * FROM gmus.geologic_units_with_intervals WHERE upper(state) in (SELECT postal FROM states)) SELECT gid AS id, state, a.rocktype1, a.rocktype2, b.rocktype3, a.unit_name, b.unit_age, a.unitdesc, a.strat_unit, a.unit_com, a.interval_color AS color, ST_AsGeoJSON(ST_Intersection(the_geom, (SELECT buffer FROM linestring))) AS geometry FROM subset a JOIN gmus.units b ON a.unit_link = b.unit_link WHERE ST_Intersects(the_geom::geography, (SELECT buffer FROM linestring)) is true", [req.query.line, buffer], function(error, result) {
      if (error) {
        larkin.error(req, res, next, "Something went wrong");
      } else {
        dbgeo.parse({
          "data": result.rows,
          "outputFormat": (req.query.format) ? larkin.getOutputFormat(req.query.format) : "geojson",
          "callback": function(error, result) {
            if (error) {
              larkin.error(req, res, next, "Something went wrong");
            } else {
              larkin.sendData(gp(result, 4), res, "json", next);
            }
          }
        });
      }
    });
  }
  
}
