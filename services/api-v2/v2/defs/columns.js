var api = require("../api"),
    larkin = require("../larkin");

module.exports = function(req, res, next) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }

  var sql = "SELECT cols.id AS col_id, col_group_id, col_name, GROUP_CONCAT(DISTINCT ref_id SEPARATOR '|') AS ref_id, status_code AS status, count(distinct units_sections.unit_id) AS t_units  FROM cols LEFT JOIN col_refs ON col_id=cols.id LEFT JOIN units_sections ON units_sections.col_id = cols.id ",
      where = [],
      params = {};

  if ("all" in req.query) {
    // do nothing
  } else if (req.query.col_id) {
    where.push("cols.id in (:col_id)");
    params["col_id"] = larkin.parseMultipleIds(req.query.col_id);

  } else if (req.query.col_group_id) {
    where.push("cols.col_group_id IN (:col_group_id)");
    params["col_group_id"] = larkin.parseMultipleIds(req.query.col_group_id);

  } else if (req.query.col_name) {
    where.push("cols.col_name = :col_name");
    params["col_name"] = req.query.col_name;

  }

  if (req.query.status) {
    where.push("status_code = :status");
    params["status"] = req.query.status;
  }

  if (where.length > 0) {
    sql += " WHERE " + where.join(" AND ");
  }

  sql += " GROUP BY cols.id";

  if ("sample" in req.query) {
    sql += " LIMIT 5";
  }

  larkin.query(sql, params, function(error, result) {
    if (error) {
      return larkin.error(req, res, next, error);
    }

    result.forEach(function(d) {
      d.ref_id = larkin.jsonifyPipes(d.ref_id, "integers");
    });

    larkin.sendData(req, res, next, {
      format: (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json",
      bare: (api.acceptedFormats.bare[req.query.format]) ? true : false,
      refs: 'ref_id'
    }, {
      data: result
    });
  });
}
