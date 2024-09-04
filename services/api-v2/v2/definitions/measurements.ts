var api = require("../api"),
  larkin = require("../larkin");

module.exports = function (req, res, next, cb) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }

  var sql =
      `SELECT measurements.id AS measure_id,
       measurement AS name, 
       measurement_type AS type, 
       measurement_class AS class, 
       COUNT(DISTINCT unit_measures.unit_id)::integer AS t_units 
FROM macrostrat_temp.measurements 
    LEFT JOIN macrostrat_temp.measures ON measures.measurement_id = measurements.id 
    LEFT JOIN macrostrat_temp.unit_measures ON unit_measures.measuremeta_id = measures.measuremeta_id
    `,
    params = {};

  if (req.query.all) {
    // do nothing
  } else if (req.query.measurement_class) {
    sql += " WHERE measurement_class = :measurement_class";
    params["measurement_class"] = req.query.measurement_class;
  } else if (req.query.measurement_type) {
    sql += " WHERE measurement_type = :measurement_type";
    params["measurement_type"] = req.query.measurement_type;
  } else if (req.query.measurement) {
    sql += " WHERE measurement = :measurement";
    params["measurement"] = req.query.measurement;
  } else if (req.query.measure_id) {
    sql += " WHERE measurements.id = ANY(:measure_id) ";
    params["measure_id"] = larkin.parseMultipleIds(req.query.measure_id);
  }

  sql += " GROUP BY measurements.id";

  if ("sample" in req.query) {
    sql += " LIMIT 5";
  }

  larkin.queryPg("burwell", sql, params, function (error, data) {
    if (error) {
      if (error) {
        return cb(error);
      } else {
        return larkin.error(req, res, next, error);
      }
    }

    if (cb) {
      cb(null, data.rows);
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
        },
        {
          data: data.rows,
        },
      );
    }
  });
};
