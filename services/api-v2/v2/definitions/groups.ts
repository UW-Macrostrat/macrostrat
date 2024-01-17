var api = require("../api"),
  larkin = require("../larkin");

module.exports = function (req, res, next, cb) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }

  var sql =
      "SELECT col_groups.id AS col_group_id, col_group, col_group_long AS name, COUNT(DISTINCT cols.id) AS t_cols, COUNT(DISTINCT units_sections.unit_id) AS t_units, cols.project_id FROM col_groups LEFT JOIN cols ON cols.col_group_id = col_groups.id LEFT JOIN units_sections ON units_sections.col_id = cols.id ",
    params = {};

  if (req.query.col_group_id) {
    sql += " WHERE col_groups.id IN (:col_group_ids)";
    params["col_group_ids"] = larkin.parseMultipleIds(req.query.col_group_id);
  } else if (req.query.project_id) {
    sql += " WHERE cols.project_id IN (:project_id)";
    params["project_id"] = larkin.parseMultipleIds(req.query.project_id);
  } else if (req.query.col_id) {
    sql += " WHERE cols.id IN (:col_id)";
    params["col_id"] = larkin.parseMultipleIds(req.query.col_id);
  }

  sql += " GROUP BY col_groups.id ";

  if ("sample" in req.query) {
    sql += " LIMIT 5";
  }

  larkin.query(sql, params, function (error, data) {
    if (error) {
      if (cb) {
        cb(error);
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
