var api = require("../api"),
  larkin = require("../larkin");

module.exports = function (req, res, next, cb) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }
  //There will be a discrepancy with a key in production. Updated in_proccess_cols to in_process_cols key. Values are
  //still the same.

  const where = [];
  let params = {};

  if (req.query.project_id) {
    where.push("projects.id = ANY(:project_id)");
    params["project_id"] = larkin.parseMultipleIds(req.query.project_id);
  }

  const whereStatement = where.length > 0 ? where.join(" AND ") : "true";

  let sql = `
    SELECT
        p.id AS project_id,
        p.project,
        p.descrip,
        p.timescale_id,
        count(DISTINCT units_sections.col_id)::integer AS t_cols,
        count(DISTINCT cols.id) FILTER ( WHERE cols.status_code = 'active' )::integer AS active_cols,
        count(DISTINCT cols.id) FILTER ( WHERE cols.status_code = 'in process' )::integer AS in_process_cols,
        count(DISTINCT cols.id) FILTER ( WHERE cols.status_code = 'obsolete' )::integer AS obsolete_cols,
        count(DISTINCT units_sections.unit_id)::integer AS t_units,
        coalesce(round(sum(DISTINCT cols.col_area) FILTER ( WHERE cols.status_code = 'active')), 0) AS area
    FROM macrostrat.projects p
    LEFT JOIN macrostrat.cols ON p.id = cols.project_id
    LEFT JOIN macrostrat.units_sections ON units_sections.col_id = cols.id
    WHERE ${whereStatement}
    GROUP BY
      p.id,
      p.project,
      p.descrip,
      p.timescale_id
  `;

  if (larkin.hasCapability("composite-projects")) {
    /** Progressive enhancement for composite projects **/
    sql = `
    WITH composite_tree AS (
      SELECT pt.parent_id,  array_agg(pt.child_id) children, jsonb_agg(to_jsonb(p)) AS members
      FROM macrostrat.projects_tree pt
      JOIN LATERAL (
        SELECT p.id, p.slug, p.project name
        FROM macrostrat.projects p
        WHERE p.id = pt.child_id
      ) AS p ON true
      GROUP BY pt.parent_id
    )
    SELECT
        p.id AS project_id,
        p.slug,
        p.project,
        p.descrip,
        p.timescale_id,
        ct.members,
        count(DISTINCT units_sections.col_id)::integer AS t_cols,
        count(DISTINCT cols.id) FILTER ( WHERE cols.status_code = 'active' )::integer AS active_cols,
        count(DISTINCT cols.id) FILTER ( WHERE cols.status_code = 'in process' )::integer AS in_process_cols,
        count(DISTINCT cols.id) FILTER ( WHERE cols.status_code = 'obsolete' )::integer AS obsolete_cols,
        count(DISTINCT units_sections.unit_id)::integer AS t_units,
        coalesce(round(sum(DISTINCT cols.col_area) FILTER ( WHERE cols.status_code = 'active')), 0) AS area
    FROM macrostrat.projects p
    LEFT JOIN composite_tree ct
      ON ct.parent_id = p.id
    LEFT JOIN macrostrat.cols ON p.id = cols.project_id
          OR (p.is_composite AND cols.project_id = ANY(ct.children))
    LEFT JOIN macrostrat.units_sections ON units_sections.col_id = cols.id
    WHERE ${whereStatement}
    GROUP BY
      p.id,
      p.project,
      p.descrip,
      p.timescale_id,
      p.slug,
      ct.children,
      ct.members
    `;
  }

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
