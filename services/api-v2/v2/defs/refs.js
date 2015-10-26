var api = require("../api"),
    larkin = require("../larkin");

module.exports = function(req, res, next) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }

  var sql = "SELECT refs.id AS ref_id, pub_year, author, ref, doi, url, COUNT(DISTINCT units_sections.unit_id) AS t_units FROM refs LEFT JOIN col_refs ON col_refs.ref_id = refs.id LEFT JOIN units_sections ON units_sections.col_id = col_refs.col_id",
      params = {};

  if ("all" in req.query) {
    // do nothing
  } else if (req.query.ref_id) {
    sql += " WHERE refs.id IN (:ref_id)";
    params["ref_id"] = larkin.parseMultipleIds(req.query.ref_id);

  }

  sql += " GROUP BY refs.id";

  if ("sample" in req.query) {
    sql += " LIMIT 5";
  }

  larkin.query(sql, params, function(error, data) {
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
