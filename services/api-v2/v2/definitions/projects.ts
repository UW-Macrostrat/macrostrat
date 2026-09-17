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
    where.push("p.id = ANY(:project_id)");
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
    ),
    /* The columns each project counts: its own, plus its members' for a
       composite. Resolved on its own so the aggregates below group by a bare
       project id. Grouping the aggregate directly by the composite's \`members\`
       jsonb and \`children\` array made Postgres sort every
       project x column x unit_section row on that wide key — half a million
       rows spilling ~136 MB to disk, and about a second of the request. */
    project_cols AS (
      SELECT
        p.id AS project_id,
        cols.id AS col_id,
        cols.status_code,
        cols.col_area
      FROM macrostrat.projects p
      LEFT JOIN composite_tree ct
        ON ct.parent_id = p.id
      LEFT JOIN macrostrat.cols ON p.id = cols.project_id
            OR (p.is_composite AND cols.project_id = ANY(ct.children))
      WHERE ${whereStatement}
    ),
    project_stats AS (
      SELECT
        pc.project_id,
        count(DISTINCT units_sections.col_id)::integer AS t_cols,
        count(DISTINCT pc.col_id) FILTER ( WHERE pc.status_code = 'active' )::integer AS active_cols,
        count(DISTINCT pc.col_id) FILTER ( WHERE pc.status_code = 'in process' )::integer AS in_process_cols,
        count(DISTINCT pc.col_id) FILTER ( WHERE pc.status_code = 'obsolete' )::integer AS obsolete_cols,
        count(DISTINCT units_sections.unit_id)::integer AS t_units,
        coalesce(round(sum(DISTINCT pc.col_area) FILTER ( WHERE pc.status_code = 'active')), 0) AS area
      FROM project_cols pc
      LEFT JOIN macrostrat.units_sections ON units_sections.col_id = pc.col_id
      GROUP BY pc.project_id
    )
    SELECT
        p.id AS project_id,
        p.slug,
        p.project,
        p.descrip,
        p.timescale_id,
        ct.members,
        ps.t_cols,
        ps.active_cols,
        ps.in_process_cols,
        ps.obsolete_cols,
        ps.t_units,
        ps.area
    FROM macrostrat.projects p
    LEFT JOIN composite_tree ct
      ON ct.parent_id = p.id
    LEFT JOIN project_stats ps
      ON ps.project_id = p.id
    WHERE ${whereStatement}
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
