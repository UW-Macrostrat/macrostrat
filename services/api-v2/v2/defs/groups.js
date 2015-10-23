var api = require("../api"),
    larkin = require("../larkin");

module.exports = function(req, res, next) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }

  var sql = "SELECT col_groups.id AS col_group_id, col_group, col_group_long AS name, COUNT(DISTINCT units_sections.unit_id) AS t_units FROM col_groups LEFT JOIN cols ON cols.col_group_id = col_groups.id LEFT JOIN units_sections ON units_sections.col_id = cols.id ",
      params = {};

  if (req.query.col_group_id) {
    sql += " WHERE col_groups.id IN (:col_group_ids)";
    params["col_group_ids"] = larkin.parseMultipleIds(req.query.col_group_id);
  }

  sql += " GROUP BY col_groups.id ";

  if ("sample" in req.query) {
    sql += " LIMIT 5";
  }

  larkin.query(sql, params, function(error, data) {
    if (error) {
      return larkin.error(req, res, next, error);
    }

    larkin.sendData(data, res, ((api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json"), next);

  });
}
