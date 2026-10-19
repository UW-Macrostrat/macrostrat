var api = require("../api"),
  larkin = require("../larkin");

module.exports = function (req, res, next, cb) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }

  var sql =
      "SELECT name, COALESCE(iso639_3, '') AS iso639_3, COALESCE(iso639_1, '') AS iso639_1 FROM languages WHERE iso639_3 IS NOT NULL",
    params = [];

  if (req.query.name) {
    sql += " AND name ILIKE ANY($1)";
    params.push(larkin.parseMultipleStrings(req.query.name));
  }

  if (req.query.code) {
    sql +=
      " AND (iso639_3 ILIKE ANY($" +
      (params.length + 1) +
      ") OR iso639_1 ILIKE ANY($" +
      (params.length + 1) +
      "))";
    params.push(larkin.parseMultipleStrings(req.query.code));
  }

  if ("sample" in req.query) {
    sql += " LIMIT 5";
  }

  larkin.queryPg("wof", sql, params, function (error, result) {
    if (error) {
      if (cb) {
        return cb(error);
      } else {
        return larkin.error(req, res, next, error);
      }
    } else {
      if (cb) {
        cb(null, result.rows);
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
            data: result.rows,
          },
        );
      }
    }
  });
};
