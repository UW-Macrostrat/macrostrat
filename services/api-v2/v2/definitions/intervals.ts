//This endpoint requires trailing / for it to execute. We'll need to handle non-trailing / as well.
//Ex.   {{LocalHost}}defs/intervals/   executes, {{LocalHost}}defs/intervals   does not execute.

var api = require("../api"),
  larkin = require("../larkin");

module.exports = function (req, res, next, cb) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }

  //updated params back to dict
  let params = {}
  let where = []
  let where_final= "";
  let groupby = "";
  let limit = "";
  let color = "";


  if (req.query.timescale) {
    where.push("timescale ILIKE :timescale");
    params["timescale"] = req.query.timescale;
  }
  else if (req.query.timescale_id) {
    where.push("timescales.id = ANY(:timescale_id)");
    params["timescale_id"] = larkin.parseMultipleIds(req.query.timescale_id);
  }

  if (req.query.name) {
    where.push("intervals.interval_name ILIKE :name");
    params["name"] = req.query.name;
  }

  if (req.query.name_like) {
    where.push("intervals.interval_name ILIKE :name_like");
    //may want to update to "%" + req.query.name_like + "%"
    params["name_like"] = req.query.name_like + "%";
  }

  if (req.query.int_id) {
    where.push("intervals.id = ANY(:int_id)");
    params["int_id"] = larkin.parseMultipleIds(req.query.int_id);
  }

  if (req.query.b_age && req.query.t_age) {
    if (req.query.rule === "contains") {
      where.push(
        "intervals.age_top >= :t_age AND intervals.age_bottom <= :b_age",
      );
      params["b_age"] = req.query.b_age;
      params["t_age"] = req.query.t_age;
    }
    else if (req.query.rule === "exact") {
      where.push(
        "intervals.age_top = :t_age AND intervals.age_bottom = :b_age",
      );
      params["b_age"] = req.query.b_age;
      params["t_age"] = req.query.t_age;
    }
    else {
      where.push(
        "intervals.age_bottom > :t_age AND intervals.age_top < :b_age",
      );
      params["b_age"] = req.query.b_age;
      params["t_age"] = req.query.t_age;
    }
  }
  else if (req.query.age) {
    where.push("intervals.age_top <= :age AND intervals.age_bottom >= :age");
    params["age"] = req.query.age;
  }

  groupby = "GROUP BY intervals.id, interval_name, interval_abbrev, age_top, age_bottom, interval_type, ";


  if (req.query.true_colors) {
    color = "orig_color AS color ";
    groupby += "orig_color ORDER BY age_top ASC";
  } else {
    color = "interval_color AS color ";
    groupby += "interval_color ORDER BY age_top ASC";

  }

  if (where.length > 0) {
    where_final = "WHERE " + where.join(" AND ");
  }

  if ("sample" in req.query) {
    limit = "LIMIT 5";
  }

  let sql = `SELECT intervals.id AS int_id,
         interval_name AS name,
         interval_abbrev AS abbrev,
         age_top AS t_age,
         age_bottom AS b_age,
         interval_type AS int_type,
         ${color},
        json_agg(json_build_object(
             'timescale_id', timescales.id,
             'name', timescales.timescale
         )) AS timescales
    FROM macrostrat.intervals
    LEFT JOIN macrostrat.timescales_intervals ON intervals.id = macrostrat.timescales_intervals.interval_id
    LEFT JOIN macrostrat.timescales ON macrostrat.timescales.id = macrostrat.timescales_intervals.timescale_id
    ${where_final}
    ${groupby}
    ${limit}
  `;

  larkin.queryPg("burwell",
      sql,
      params, function (error, result) {
    if (error) {
      if (cb) {
        cb(error);
      } else {
        return larkin.error(req, res, next, "Something went wrong");
      }
    }

    else {
      /*
      if (req.query.format !== "csv" || req.query.format == undefined) {
        result.rows.forEach(function (d) {
          d.timescale_id = larkin.jsonifyPipes(d.timescale_id, "integers");
          if (d.timescales) {
            d.timescales = d.timescales.split("|").map(function (j) {
              return {
                timescale_id: parseInt(j.split("--")[1]),
                name: j.split("--")[0],
              };
            });
          } else {
            d.timescales = [];
          }
        });
      } */


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
          },
          {
            data: result.rows,
          },
        );
      }
    }
  });
};
