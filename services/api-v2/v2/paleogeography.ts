var api = require("./api"),
  async = require("async"),
  dbgeo = require("dbgeo"),
  larkin = require("./larkin");
//TODO test this endpoint. cannot test error: relation "earthbyte2013_raw.reconstructed_2" does not exist
module.exports = function (req, res, next) {
  if (!req.query.age && !req.query.interval_name && !("sample" in req.query)) {
    larkin.info(req, res, next);
  } else {
    async.waterfall(
      [
        function (callback) {
          let params = {}
          if (req.query.age) {
            callback(null, req.query.age);
          } else if (req.query.interval_name) {
              let sql = `SELECT (age_bottom + age_top)/2 AS mid FROM macrostrat_temp.intervals WHERE interval_name = :interval_name`
              params['interval_name'] = req.query.interval_name
            larkin.queryPgMaria("macrostrat_two",
              sql,
               params,
              function (error, result) {
                if (error) {
                  callback(error);
                } else {
                  if (result.length === 1) {
                    callback(null, parseInt(result[0].mid));
                  } else {
                    larkin.error(req, res, next, "interval not found");
                  }
                }
              },
            );
          } else if ("sample" in req.query) {
            callback(null, 0);
          } else {
            callback("error");
          }
        },
        function (year, callback) {
          var limit = "sample" in req.query ? " LIMIT 5" : "";
          larkin.queryPg(
            "alice",
            "SELECT plateid1::integer AS plate_id, ST_AsGeoJSON(geom) AS geometry FROM earthbyte2013_raw.reconstructed_" +
              year +
              limit,
            [],
            function (error, result) {
              callback(null, result);
            },
          );
        },
      ],
      function (error, data) {
        if (error) {
          larkin.error(req, res, next, "Invalid query");
        } else {
          dbgeo.parse(
            data,
            {
              geometryType: "geojson",
              geometryColumn: "geometry",
              outputFormat: larkin.getOutputFormat(req.query.format),
            },
            function (error, result) {
              if (error) {
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
        }
      },
    );
  }
};
