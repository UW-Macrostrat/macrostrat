var api = require("../api"),
    larkin = require("../larkin");

module.exports = function(req, res, next) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }
  
  var sql = "SELECT col AS col_id, col_group_id, col_name FROM cols",
      params = [];

  if ("all" in req.query) {
    // do nothing
  } else if (req.query.col_id) {
    sql += " WHERE id = ?";
    params.push(req.query.col_id);

  } else if (req.query.col_group_id) {
    sql += " WHERE col_group_id = ?";
    params.push(req.query.col_group_id);

  } else if (req.query.col_name) {
    sql += " WHERE col_name = ?";
    params.push(req.query.col_name);

  }

  var format = (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json";
  larkin.query(sql, params, null, true, res, format, next);
}
