var api = require("./api");
var dbgeo = require("dbgeo");
var larkin = require("./larkin");

// need to fix bug to allow both col_id and measurement type parameters at same time

module.exports = function (req, res, next) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  } else if (req.query.measurement_type || req.query.measurement_class) {
    if (
      req.query.unit_id ||
      req.query.section_id ||
      req.query.col_id ||
      req.query.project_id ||
      req.query.measuremeta_id ||
      "sample" in req.query ||
      req.query.response === "light"
    ) {
    } else {
      return larkin.error(
        req,
        res,
        next,
        "You must specify a specific measurement or a unit_id,section_id,col_id, project_id, or measuremeta_id to retrieve these data; or, include the sample parameter",
      );
    }
  } else if (
    req.query.unit_id ||
    req.query.section_id ||
    req.query.col_id ||
    req.query.project_id ||
    req.query.measuremeta_id ||
    "sample" in req.query ||
    req.query.measure_id ||
    req.query.measurement ||
    req.query.measurement_id ||
    req.query.response === "light"
  ) {
  } else if (req.query.lith_id || req.query.lith_type || req.query.lith_class) {
    if (
      req.query.measurement ||
      req.query.measurement_id ||
      req.query.measurement_type ||
      "sample" in req.query ||
      !("show_values" in req.query)
    ) {
    } else {
      return larkin.error(
        req,
        res,
        next,
        "You must specify a measurement, measurement_id, or measurement_type to retrieve these data or include the sample parameter to see example output",
      );
    }
  } else {
    return larkin.error(
      req,
      res,
      next,
      "Invalid Parameters. Note that available data volume may require more precise specification in the request. See parameter list below and try restricting search based on geology or measurement, mesurement_type.",
    );
  }

  var where = [];
  var params = [];
  var limit = "";

  var geo =
    req.query.format && api.acceptedFormats.geo[req.query.format]
      ? true
      : false;

  var validParams = {
    measurement: "measurements.measurement",
    measurement_type: "measurements.measurement_type",
    measurement_class: "measurements.measurement_class",
    measurement_id: "measurements.id",
    measure_id: "measures.id",
    measuremeta_id: "measuremeta.id",
    lith_id: "measuremeta.lith_id",
    unit_id: "unit_measures.unit_id",
    section_id: "units_sections.section_id",
    measure_phase: "measures.measure_phase",
    project_id: "cols.project_id",
  };

  Object.keys(req.query).forEach(function (param) {
    if (validParams.hasOwnProperty(param)) {
      where.push(validParams[param] + " IN (:" + param + ")");

      if (param.substr(param.length - 3, param.length) === "_id") {
        params[param] = larkin.parseMultipleIds(req.query[param]);
      } else {
        params[param] = larkin.parseMultipleStrings(req.query[param]);
      }
    }
  });

  if (req.query.col_id) {
    where.push(
      "(measuremeta_cols.col_id IN (:col_id1) OR units_sections.col_id IN (:col_id2))",
    );
    params["col_id1"] = larkin.parseMultipleIds(req.query.col_id);
    params["col_id2"] = larkin.parseMultipleIds(req.query.col_id);
  }

  if (req.query.interval_name) {
    where.push(
      "b_age>(SELECT age_top from intervals where interval_name IN (:intname1) and t_age<(SELECT age_bottom from intervals where interval_name in (:intname2)))",
    );
    params["intname1"] = larkin.parseMultipleStrings(req.query.interval_name);
    params["intname2"] = larkin.parseMultipleStrings(req.query.interval_name);
  }

  if (req.query.lith_type) {
    where.push("lith_type IN (:lith_type)");
    params["lith_type"] = larkin.parseMultipleStrings(req.query.lith_type);
  }

  if (req.query.lith_class) {
    where.push("lith_class IN (:lith_class)");
    params["lith_class"] = larkin.parseMultipleStrings(req.query.lith_class);
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
    measurements.id as measurement_id,
    measuremeta.id as measuremeta_id,
    measurement,
    units as measure_units,
    measure_phase,
    method,
    count(measurements.id) as n,
    measuremeta.ref_id`;

  if (req.query.response === "long") {
    select += `,
      sample_name,
      sample_geo_unit as geo_unit,
      sample_lith as samp_lith,
      measuremeta.lith_id as samp_lith_id,
      sample_descrip as samp_desc,
      measuremeta.age as samp_age,
      measuremeta.lat as lat,
      measuremeta.lng as lng,
      unit_measures.unit_id,
      rel_position as unit_rel_pos,
      IF(unit_measures.unit_id is not null, units_sections.col_id, measuremeta_cols.col_id) as col_id,
      strat_name_id,
      match_basis,
      ref`;
  }

  if (req.query.response === "light") {
    select = `
      measurements.id as measurement_id,
      measuremeta.id as measuremeta_id,
      units as measure_units,
      count(measurements.id) as n,
      unit_measures.unit_id,
      measuremeta.ref_id`;
  }

  if (geo && req.query.response !== "long") {
    select += ", measuremeta.lat as lat, measuremeta.lng as lng";
  }

  if ("show_values" in req.query) {
    select += `,
            GROUP_CONCAT(measure_value ORDER BY measures.id SEPARATOR '|') AS measure_value,
            GROUP_CONCAT(v_error ORDER BY measures.id SEPARATOR '|') AS measure_error `;
    if (req.query.response !== "light")
      select +=
        ", GROUP_CONCAT(samp_pos order by measures.id SEPARATOR '|') AS measure_position";
    if (req.query.response === "long")
      select +=
        ", GROUP_CONCAT(v_n ORDER BY measures.id SEPARATOR '|') AS measure_n, GROUP_CONCAT(sample_no ORDER BY measures.id SEPARATOR '|') AS sample_no";
    select += ", v_error_units as error_units";
  }

  var sql = `SELECT
    ${select}
    FROM measures
    JOIN measurements on measurement_id=measurements.id
    JOIN measuremeta ON measuremeta.id=measures.measuremeta_id
	  LEFT JOIN unit_measures ON unit_measures.measuremeta_id=measuremeta.id
    LEFT JOIN measuremeta_cols ON measuremeta.id=measuremeta_cols.measuremeta_id
    LEFT JOIN units_sections USING (unit_id)
    LEFT JOIN cols ON units_sections.col_id=cols.id
    LEFT JOIN lookup_unit_intervals USING (unit_id)
    LEFT JOIN liths ON lith_id=liths.id
    ${where}
    GROUP BY measuremeta.id,measurements.id
    ${limit}
  `;
  // console.log(sql)

  larkin.query(sql, params, function (error, response) {
    if (error) {
      larkin.error(req, res, next, error);
    } else {
      if (req.query.format !== "csv" && "show_values" in req.query) {
        for (var i = 0; i < response.length; i++) {
          if (req.query.response !== "light") {
            response[i].measure_position = larkin.jsonifyPipes(
              response[i].measure_position,
              "floats",
            );
          }
          response[i].measure_value = larkin.jsonifyPipes(
            response[i].measure_value,
            "floats",
          );
          response[i].measure_error = larkin.jsonifyPipes(
            response[i].measure_error,
            "floats",
          );
          if (req.query.response === "long") {
            response[i].measure_n = larkin.jsonifyPipes(
              response[i].measure_n,
              "floats",
            );
            response[i].sample_no = larkin.jsonifyPipes(
              response[i].sample_no,
              "strings",
            );
          }
        }
      }

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
                  data: response,
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
            data: response,
          },
        );
      }
    }
  });
};
