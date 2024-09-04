var api = require("../api"),
  larkin = require("../larkin");

module.exports = function (req, res, next, cb) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }

  let sql =
      `SELECT environs.id AS environ_id, 
       environ AS name, 
       environ_type AS type, 
       environ_class AS class, 
       environ_color AS color, 
       COUNT(distinct units_sections.unit_id) AS t_units 
    FROM macrostrat_temp.environs 
        LEFT JOIN macrostrat_temp.unit_environs ON unit_environs.environ_id = environs.id 
        LEFT JOIN macrostrat_temp.units_sections ON units_sections.unit_id = unit_environs.unit_id
    `
  let environ = {};

  if (req.query.all) {
    // do nothing
  } else if (req.query.environ_class) {
    sql += "WHERE environ_class = :environ_class";
    environ["environ_class"] = req.query.environ_class;
  } else if (req.query.environ_type) {
    sql += "WHERE environ_type = :environ_type";
    environ["environ_type"] =req.query.environ_type;
  } else if (req.query.environ) {
    sql += "WHERE environ = :environ";
    environ["environ"] = req.query.environ;
  } else if (req.query.environ_id) {
    sql += "WHERE environs.id = :environ_id";
    environ["environ_id"]= req.query.environ_id;
  }

  sql += "\nGROUP BY environs.id\n";

  if ("sample" in req.query) {
    sql += " LIMIT 5";
  }
  larkin.queryPg("burwell", sql, environ, function (error, data) {
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
