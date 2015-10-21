var api = require("./api"),
    larkin = require("./larkin"),
    multiline = require("multiline");

module.exports = function(req, res, next) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }

  var sql = multiline(function() {/*
    SELECT
      project_id,
      project,
      columns,
      packages,
      units,
      pbdb_collections,
      measurements
    FROM stats
  */});

  var format = (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json";

  larkin.query(sql, [], null, true, res, format, next);
}
