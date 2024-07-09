var api = require("../api"),
  larkin = require("../larkin");

module.exports = function (req, res, next, cb) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }

  var sql =
    `SELECT intervals.id AS int_id,
     interval_name AS name,
     interval_abbrev abbrev,
     age_top AS t_age,
     age_bottom AS b_age,
     interval_type AS int_type,
     STRING_AGG(timescales.timescale || '--' || timescales.id, '|') AS timescales,
     `

  if (req.query.true_colors) {
    sql += "orig_color AS color ";
  } else {
    sql += "interval_color AS color ";
  }

  let params = []
  let where = []

  sql += `
  FROM macrostrat_temp.intervals 
  LEFT JOIN macrostrat_temp.timescales_intervals ON interval_id=intervals.id 
  LEFT JOIN macrostrat_temp.timescales ON timescale_id=timescales.id\n `
  console.log(sql)
  let count = 1

  if (req.query.timescale) {
    where.push(` timescale = $${count}`);
    params.push(req.query.timescale);
    count++;
  } else if (req.query.timescale_id) {
    where.push(`timescales.id = ANY($${count})`);
    params.push(larkin.parseMultipleIds(req.query.timescale_id));
    count++;
    console.log(where)
    console.log(params)
  }

  if (req.query.name) {
    where.push(`intervals.interval_name LIKE $${count}`);
    params.push(req.query.name);
    count++;
  }

  if (req.query.name_like) {
    where.push(`intervals.interval_name LIKE $${count}`);
    //may want to update to "%" + req.query.name_like + "%"
    params.push(req.query.name_like + "%");
    count++;
  }

  if (req.query.int_id) {
    where.push(`intervals.id = ANY($${count})`);
    params.push(larkin.parseMultipleIds(req.query.int_id));
    count++;
  }

  if (req.query.b_age && req.query.t_age) {
    if (req.query.rule === "contains") {
      where.push(
        "intervals.age_top >= :t_age AND intervals.age_bottom <= :b_age",
      );
      params["b_age"] = req.query.b_age;
      params["t_age"] = req.query.t_age;
    } else if (req.query.rule === "exact") {
      where.push(
        "intervals.age_top = :t_age AND intervals.age_bottom = :b_age",
      );
      params["b_age"] = req.query.b_age;
      params["t_age"] = req.query.t_age;
    } else {
      where.push(
        "intervals.age_bottom > :t_age AND intervals.age_top < :b_age",
      );
      params["b_age"] = req.query.b_age;
      params["t_age"] = req.query.t_age;
    }
  } else if (req.query.age) {
    where.push("intervals.age_top <= :age AND intervals.age_bottom >= :age");
    params["age"] = req.query.age;
  }

  if (where.length > 0) {
    sql += "WHERE " + where.join(" AND ") + "\n";
  }

  sql += " GROUP BY intervals.id, age_top\n" +
      "ORDER BY age_top ASC\n";

  if ("sample" in req.query) {
    sql += " LIMIT 5";
  }
  console.log(sql)
  console.log(params)

  larkin.queryPgMaria("macrostrat_two",
      sql,
      params, function (error, result) {
    if (error) {
      if (cb) {
        cb(error);
      } else {
        return larkin.error(req, res, next, "Something went wrong");
      }
    } /*else {
      if (req.query.format !== "csv") {
        result.forEach(function (d) {
          //  d.timescale_id = larkin.jsonifyPipes(d.timescale_id, "integers");
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
      }*/

      if (cb) {
        cb(null, result);
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
            data: result,
          },
        );
      };
    });
  };
//};
