var api = require("./api"),
    async = require("async"),
    dbgeo = require("dbgeo"),
    gp = require("geojson-precision"),
    larkin = require("./larkin");

module.exports = function(req, res, next) {
  if (Object.keys(req.query).length < 1 || !req.query.line) {
    larkin.info(req, res, next);
  } else {
    var types = (req.query.type) ? req.query.type.split(",") : ["gmna", "gmus"];
    async.parallel({
      gmna: function(callback) {
        if (types.indexOf("gmna") > -1) {
          larkin.queryPg("earthbase", "WITH linestring AS (SELECT ST_Buffer($1::geography, 35000) AS buffer) SELECT objectid AS id, unit_abbre, rocktype, lithology AS lith, min_age, max_age, interval_color AS color, ST_AsGeoJSON(ST_Intersection(the_geom, (SELECT buffer FROM linestring))) AS geometry FROM gmna.gmna_for_maps WHERE ST_Intersects(the_geom, (SELECT buffer FROM linestring)) is true", [req.query.line], function(error, result) {
              if (error) {
                callback(error);
              } else {
                dbgeo.parse({
                  "data": result.rows,
                  "outputFormat": "geojson",
                  "callback": function(error, result) {
                    if (error) {
                      callback(error);
                    } else {
                      callback(null, gp(result, 4));
                    }
                  }
                });
              }
          });
        } else {
          callback(null);
        }
      },
      
      gmus: function(callback) {
        if (types.indexOf("gmus") > -1) {
          larkin.queryPg("earthbase", "WITH linestring AS (SELECT ST_Buffer($1::geography, 35000) AS buffer), states as (SELECT postal FROM us_states WHERE ST_Intersects(geom::geography, (SELECT buffer FROM linestring))), subset as (SELECT * FROM gmus.geologic_units_with_intervals WHERE upper(state) in (SELECT postal FROM states)) SELECT gid AS id, state, a.rocktype1, a.rocktype2, b.rocktype3, a.unit_name, b.unit_age, a.unitdesc, a.strat_unit, a.unit_com, a.interval_color AS color, ST_AsGeoJSON(ST_Intersection(the_geom, (SELECT buffer FROM linestring))) AS geometry FROM subset a JOIN gmus.units b ON a.unit_link = b.unit_link WHERE ST_Intersects(the_geom::geography, (SELECT buffer FROM linestring)) is true", [req.query.line], function(error, result) {
              if (error) {
                callback(error);
              } else {
                dbgeo.parse({
                  "data": result.rows,
                  "outputFormat": "geojson",
                  "callback": function(error, result) {
                    if (error) {
                      callback(error);
                    } else {
                      callback(null, gp(result, 4));
                    }
                  }
                });
              }
          });
        } else {
          callback(null);
        }
      }
    }, function(error, results) {
      if (error) {
        larkin.error(req, res, next, "Something went wrong");
      } else {
        larkin.sendData(results, res, "json", next);
      }
    });
  }
}
