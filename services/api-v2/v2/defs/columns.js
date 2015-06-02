var api = require("../api"),
    larkin = require("../larkin");

module.exports = function(req, res, next) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }
  
  var sql = "SELECT cols.id AS col_id, col_group_id, col_name, GROUP_CONCAT(DISTINCT ref_id SEPARATOR '|'), status_code status FROM cols LEFT JOIN col_refs ON col_id=cols.id GROUP BY cols.id",
      params = {};

  if ("all" in req.query) {
    // do nothing
  } else if (req.query.col_id) {
    sql += " WHERE id IN (:col_id)";
    params["col_id"] = larkin.parseMultipleIds(req.query.col_id);

  } else if (req.query.col_group_id) {
    sql += " WHERE col_group_id IN (:col_group_id)";
    params["col_group_id"] = larkin.parseMultipleIds(req.query.col_group_id);

  } else if (req.query.col_name) {
    sql += " WHERE col_name = :col_name";
    params["col_name"] = req.query.col_name;

  } else if (req.query.status) {
    sql += " WHERE status_code = :status";
    params["status"] = req.query.status;

  }

  larkin.query(sql, params, null, true, res, ((api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json"), next);
}
