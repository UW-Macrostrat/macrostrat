var api = require("../api"),
    larkin = require("../larkin");

module.exports = function(req, res, next) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }

  var sql = "SELECT id AS col_group_id, col_group, col_group_long AS name FROM col_groups",
      params = {};

  if (req.query.col_group_id) {
    sql += " WHERE id IN (:col_group_ids)";
    params["col_group_ids"] = larkin.parseMultipleIds(req.query.col_group_id);
  }

  if ("sample" in req.query) {
    sql += " LIMIT 5";
  }

  var format = (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json";
  larkin.query(sql, params, null, true, res, format, next);
}
