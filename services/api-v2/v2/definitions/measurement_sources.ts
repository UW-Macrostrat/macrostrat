var api = require("../api"),
  larkin = require("../larkin");

module.exports = function (req, res, next, cb) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }

  var sql =
      `WITH distinct_measures AS (SELECT distinct measurement_id,measuremeta_id from measures) 
SELECT refs.id AS ref_id, 
       pub_year, 
       author, 
       refs.ref, 
       refs.doi, 
       url, 
       STRING_AGG(distinct measurement::text, '|') AS measurements 
FROM macrostrat.refs 
    JOIN macrostrat.measuremeta ON refs.id=ref_id 
    JOIN macrostrat.distinct_measures ON measuremeta_id=measuremeta.id 
    JOIN macrostrat.measurements on measurement_id=measurements.id`,

    params = {};

  if ("all" in req.query) {
    // do nothing
  } else if (req.query.doi) {
    sql +=
      " WHERE (refs.doi = ANY(:doi) OR measuremeta.ref like CONCAT('http://dx.doi.org/',:doi2))";
    params["doi"] = larkin.parseMultipleStrings(req.query.doi);
    params["doi2"] = larkin.parseMultipleStrings(req.query.doi);
  } else if (req.query.measurement_class) {
    sql += " WHERE measurement_class = ANY(:measurement_class)";
    params["measurement_class"] = larkin.parseMultipleStrings(
      req.query.measurement_class,
    );
  } else if (req.query.measurement_type) {
    sql += " WHERE measurement_type = ANY(:measurement_type)";
    params["measurement_type"] = larkin.parseMultipleStrings(
      req.query.measurement_type,
    );
  } else if (req.query.measurement) {
    sql += " WHERE measurement = ANY(:measurement)";
    params["measurement"] = larkin.parseMultipleStrings(req.query.measurement);
  }

  sql += " GROUP BY refs.id";

  if ("sample" in req.query) {
    sql += " LIMIT 5";
  }


  larkin.queryPg("burwell", sql, params, function (error, data) {
    if (error) {
      if (cb) {
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
