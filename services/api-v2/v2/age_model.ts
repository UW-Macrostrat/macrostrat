var api = require("./api");
var dbgeo = require("dbgeo");
var larkin = require("./larkin");

// need to fix bug to allow both col_id and measurement type parameters at same time

module.exports = function (req, res, next) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  } else if (req.query.section_id || req.query.col_id) {
  } else {
    return larkin.error(
      req,
      res,
      next,
      "Invalid Parameters. You must specify a section_id(s) or a col_id(s).",
    );
  }

  var where = [];
  var params = {};
  var limit = "";
  var geo =
    req.query.format && api.acceptedFormats.geo[req.query.format]
      ? true
      : false;

  if (req.query.col_id) {
    where.push("units_sections.col_id = ANY(:col_id)");
    params["col_id"] = larkin.parseMultipleIds(req.query.col_id);
  }

  if (req.query.section_id) {
    where.push("units_sections.section_id = ANY(:section_id)");
    params["section_id"] = larkin.parseMultipleIds(req.query.section_id);
  }
  if (where.length) {
    where = "WHERE " + where.join(" AND ");
  } else {
    where = "";
    limit = "LIMIT 10";
  }

  if (req.query.hasOwnProperty("sample")) {
    limit = "LIMIT 10";
  }

  var select = `
    unit_boundaries.id AS boundary_id,
    units_sections.col_id,
    units_sections.section_id,
    t1 as interval_id,
    interval_name,
    age_bottom::float,
    age_top::float,
    t1_prop::float AS rel_position,
    t1_age::float AS model_age,
    boundary_status,
    boundary_type,
    boundary_position,
    unit_boundaries.unit_id as unit_below,
    unit_id_2 as unit_above,
    unit_boundaries.ref_id `;

  var sql = `SELECT
    ${select}
    FROM macrostrat_temp.unit_boundaries
    JOIN macrostrat_temp.units_sections USING (section_id)
    JOIN macrostrat_temp.intervals ON t1=intervals.id
    ${where}
    GROUP BY unit_boundaries.id, units_sections.col_id, units_sections.section_id,
         interval_name, age_bottom, age_top
    ORDER BY unit_boundaries.id ASC
    ${limit}
  `;

  var format = api.acceptedFormats.standard[req.query.format]
    ? req.query.format
    : "json";

  larkin.queryPgMaria("macrostrat_two", sql, params, function (error, response) {
    if (error) {
      larkin.error(req, res, next, error);
    } else {
      if (geo) {
        dbgeo.parse(
          response,
          {
            outputFormat: larkin.getOutputFormat(req.query.format),
            geometryColumn: ["lng", "lat"],
            geometryType: "ll",
          },
          function (error, response) {
            if (error) {
              larkin.error(req, res, next, "Something went wrong");
            } else {
              larkin.sendData(
                req,
                res,
                next,
                {
                  format: api.acceptedFormats.standard[req.query.format]
                    ? req.query.format
                    : "json",
                  bare: api.acceptedFormats.bare[req.query.format]
                    ? true
                    : false,
                  refs: "refs",
                },
                {
                  data: response.rows,
                },
              );
            }
          },
        );
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
            data: response.rows,
          },
        );
      }
    }
  });
};
