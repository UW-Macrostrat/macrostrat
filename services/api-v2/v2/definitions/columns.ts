var api = require("../api");
var larkin = require("../larkin");
var dbgeo = require("dbgeo");

module.exports = function (req, res, next, cb) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }

  //Changed GROUP_CONCAT to STRING_AGG syntax. Added schema to specify tables in PG.
  var sql = `
    SELECT
      cols.id AS col_id,
      col_group_id,
      col_name,
      lat,
      lng,
      ${req.query.format && api.acceptedFormats.geo[req.query.format] ? "lng, lat," : ""}
      col_area,
      SUM(max_thick) as max_thick,
      STRING_AGG(DISTINCT ref_id::text, '|') AS ref_id,
      status_code AS status,
      count(distinct units_sections.unit_id) AS t_units,
      project_id,
      notes
    FROM macrostrat.cols
    LEFT JOIN macrostrat.col_refs ON col_id = cols.id
    LEFT JOIN macrostrat.col_notes on cols.id=col_notes.col_id
    LEFT JOIN macrostrat.units_sections ON units_sections.col_id = cols.id
    LEFT JOIN macrostrat.units ON units_sections.unit_id=units.id
  `;
  var where = [];
  var params = {};
  //add =ANY() syntax instead of in () syntax for PG
  if (req.query.col_id) {
    where.push("cols.id = ANY(:col_id)");
    params["col_id"] = larkin.parseMultipleIds(req.query.col_id);
  }
  if (req.query.col_group_id) {
    where.push("cols.col_group_id = ANY(:col_group_id)");
    params["col_group_id"] = larkin.parseMultipleIds(req.query.col_group_id);
  }
  if (req.query.col_name) {
    where.push("cols.col_name = ANY(:col_name)");
    params["col_name"] = larkin.parseMultipleStrings(req.query.col_name);
  }

  const [whereClauses, projectParams] = larkin.buildProjectsFilter(
    req,
    "cols.project_id",
  );
  where = where.concat(whereClauses);
  Object.assign(params, projectParams);

  if (req.query.status_code || req.query.status) {
    // `status` parameter still works but has been superseded by `status_code`
    // multiple status codes can be provided
    where.push("status_code = ANY(:status_code)");
    params["status_code"] = larkin.parseMultipleIds(
      req.query.status_code ?? req.query.status,
    );
  }

  if (where.length) {
    sql += ` WHERE ${where.join(" AND ")}`;
  }
  //added group by aggregate notes
  sql += " GROUP BY cols.id, notes";

  if ("sample" in req.query) {
    sql += " LIMIT 5";
  }

  larkin.queryPg("burwell", sql, params, function (error, result) {
    if (error) {
      if (cb) {
        cb(error);
      } else {
        return larkin.error(req, res, next, error);
      }
    }

    /*TO DO: update syntax below to output correct json format
    result.forEach(function (d) {
      d.ref_id = larkin.jsonifyPipes(d.ref_id, "integers");
    });
    */

    // if a geographic format is requested
    if (req.query.format && api.acceptedFormats.geo[req.query.format]) {
      dbgeo.parse(
        result,
        {
          geometryType: "ll",
          geometryColumn: ["lng", "lat"],
          outputFormat: larkin.getOutputFormat(req.query.format),
          precision: 6,
        },
        (error, geoResult) => {
          if (error) {
            if (cb) {
              return cb(error);
            }
            return larkin.error(req, res, next, "Internal error", 500);
          }

          larkin.sendData(
            req,
            res,
            next,
            {
              format: api.acceptedFormats.standard[req.query.format]
                ? req.query.format
                : "json",
              bare: api.acceptedFormats.bare[req.query.format] ? true : false,
              refs: "ref_id",
            },
            {
              data: geoResult,
            },
          );
        },
      );
    }
    if (cb) {
      cb(null, result.rows);
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
          refs: "ref_id",
        },
        {
          data: result.rows,
        },
      );
    }
  });
};
