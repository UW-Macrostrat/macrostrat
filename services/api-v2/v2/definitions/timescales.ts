var api = require("../api"),
  larkin = require("../larkin");

module.exports = function (req, res, next, cb) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }
  var sql =
    "SELECT timescales.id AS timescale_id, timescale, count(distinct intervals.id) AS n_intervals, MAX( age_bottom ) AS max_age, MIN( age_top ) AS min_age, ref_id FROM timescales JOIN timescales_intervals ti ON ti.timescale_id = timescales.id JOIN intervals ON interval_id = intervals.id GROUP BY timescales.id ORDER BY  timescales.id ASC ";

  if ("sample" in req.query) {
    sql += " LIMIT 5";
  }

  larkin.query(sql, [], function (error, data) {
    if (error) {
      if (cb) {
        return cb(error);
      } else {
        return larkin.error(req, res, next, error);
      }
    }

    if (cb) {
      cb(null, data);
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
          data: data,
        },
      );
    }
  });
};
