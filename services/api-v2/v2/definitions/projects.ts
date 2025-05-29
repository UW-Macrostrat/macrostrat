var api = require("../api"),
  larkin = require("../larkin");

module.exports = function (req, res, next, cb) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }
  //There will be a discrepancy with a key in production. Updated in_proccess_cols to in_process_cols key. Values are
  //still the same.
  var sql = `WITH in_proc AS (
        SELECT COUNT(DISTINCT id) AS c, project_id
        FROM macrostrat.cols
        WHERE status_code = 'in process'
        GROUP BY project_id
    ),
    obs AS (
        SELECT COUNT(DISTINCT id) AS co, project_id
        FROM macrostrat.cols
        WHERE status_code = 'obsolete'
        GROUP BY project_id
    ),
    col_area_sum AS (
        SELECT project_id, SUM(col_area) AS total_area
        FROM macrostrat.cols
        WHERE status_code = 'active'
        GROUP BY project_id
    )

    SELECT
        projects.id AS project_id,
        projects.project,
        projects.descrip,
        projects.timescale_id,
        COUNT(DISTINCT units_sections.col_id)::integer AS t_cols,
        COALESCE(c, 0)::integer AS in_process_cols,
        COALESCE(co, 0)::integer AS obsolete_cols,
        COUNT(DISTINCT units_sections.unit_id)::integer AS t_units,
        COALESCE(ROUND(total_area), 0)::integer AS area

    FROM macrostrat.projects
    LEFT JOIN macrostrat.cols ON projects.id = cols.project_id
    LEFT JOIN macrostrat.units_sections ON units_sections.col_id = cols.id
    LEFT JOIN in_proc USING (project_id)
    LEFT JOIN obs USING (project_id)
    LEFT JOIN col_area_sum ON projects.id = col_area_sum.project_id
    `;

  var where = [];
  var params = {};

  if (req.query.project_id) {
    where.push("projects.id = ANY(:project_id)");
    params["project_id"] = larkin.parseMultipleIds(req.query.project_id);
  }
  if (where.length) {
    sql += ` WHERE ${where.join(" AND ")}`;
  }
  sql += `\nGROUP BY
    projects.id,
    projects.project,
    projects.descrip,
    projects.timescale_id,
    c,
    co,
    total_area;`;

  larkin.queryPg("burwell", sql, params, function (error, data) {
    if (error) {
      if (cb) {
        return cb(error);
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
        },
        {
          data: data.rows,
        },
      );
    }
  });
};