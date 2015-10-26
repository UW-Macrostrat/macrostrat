var api = require("../api"),
    larkin = require("../larkin"),
    multiline = require("multiline");

module.exports = function(req, res, next) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }

  var sql = multiline(function() {/*
    SELECT
      source_id,
      name,
      COALESCE(url, '') url,
      COALESCE(ref_title, '') ref_title,
      COALESCE(authors, '') authors,
      COALESCE(ref_year, '') ref_year,
      COALESCE(ref_source, '') ref_source,
      COALESCE(isbn_doi, '') isbn_doi,
      COALESCE(scale, '') scale
     FROM maps.sources
  */}),
      params = [];

  if ("all" in req.query) {
    // do nothing
  } else if (req.query.source_id) {
    sql += " WHERE source_id = ANY($1)";
    params.push(larkin.parseMultipleIds(req.query.source_id));
  }

  sql += " ORDER BY source_id";

  if ("sample" in req.query) {
    sql += " LIMIT 5";
  }

  larkin.queryPg("burwell", sql, params, function(error, result) {
    if (error) {
      larkin.error(req, res, next, error);
    } else {
      larkin.sendData(req, res, next, {
        format: (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json",
        bare: (api.acceptedFormats.bare[req.query.format]) ? true : false
      }, {
        data: result.rows
      });
    }
  });
}
