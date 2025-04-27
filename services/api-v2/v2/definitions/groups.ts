var api = require("../api"),
  larkin = require("../larkin");

module.exports = function (req, res, next, cb) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }
  //changes similar to structures.ts:
  //change params from dict to array. add params.push to array
  //add schema to sql table in the from and join clauses
  //change sql where syntax to = ANY($1)
  //update larkin.queryPg function

  //changing params from array back to dict
  let params = {};
  let where = [];

  if (req.query.col_group_id) {
    where.push("col_groups.id = ANY(:col_group_id)");
    params["col_group_id"] = larkin.parseMultipleIds(req.query.col_group_id);
  } else if (req.query.project_id) {
    where.push("cols.project_id = ANY(:project_id)");
    params["project_id"] = larkin.parseMultipleIds(req.query.project_id);
  } else if (req.query.col_id) {
    where.push("cols.id = ANY(:col_id)");
    params["col_id"] = larkin.parseMultipleIds(req.query.col_id);
  }

  where = where.length ? "WHERE " + where.join(" AND ") : "";

  let sql = `SELECT col_groups.id AS col_group_id,
       col_group,
       col_group_long AS name,
       COUNT(DISTINCT cols.id) AS t_cols,
       COUNT(DISTINCT units_sections.unit_id) AS t_units,
       cols.project_id
    FROM macrostrat.col_groups
    LEFT JOIN macrostrat.cols ON cols.col_group_id = col_groups.id
    LEFT JOIN macrostrat.units_sections ON units_sections.col_id = cols.id
    ${where}
    GROUP BY col_groups.id, cols.project_id `;

  if ("sample" in req.query) {
    sql += " LIMIT 5";
  }

  larkin.queryPg("burwell", sql, params, function (error, data) {
    if (error) {
      if (cb) {
        cb(error);
      } else {
        return larkin.error(req, res, next, error);
      }
    }

    if (cb) {
      cb(null, data.rows);
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
          compact: true,
        },
        {
          data: data.rows,
        },
      );
    }
  });
};
