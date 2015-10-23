var api = require("../api"),
    larkin = require("../larkin");

module.exports = function(req, res, next) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }
  var sql = "SELECT id AS timescale_id, timescale, ref_id FROM timescales";

  if ("sample" in req.query) {
    sql += " LIMIT 5";
  }

  larkin.query(sql, [], function(error, data) {
    if (error) {
      return larkin.error(req, res, next, error);
    }

    larkin.sendData(req, res, next, {
      format: (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json",
      bare: (api.acceptedFormats.bare[req.query.format]) ? true : false
    }, {
      data: data
    });

  });
}
