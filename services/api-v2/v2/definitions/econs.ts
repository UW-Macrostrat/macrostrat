//This endpoint requires trailing / for it to execute. We'll need to handle non-trailing / as well.


var api = require("../api"),
  larkin = require("../larkin");

module.exports = function (req, res, next, cb) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }

  let sql =
      `SELECT econs.id AS econ_id, 
      econ AS name, 
      econ_type AS type,
       econ_class AS class, 
       econ_color AS color, 
       COUNT(distinct units_sections.unit_id) AS t_units 
       FROM macrostrat.econs 
       LEFT JOIN macrostrat.unit_econs ON unit_econs.econ_id = econs.id 
       LEFT JOIN macrostrat.units_sections ON units_sections.unit_id = unit_econs.unit_id 
       `
  //changed params from array back to dict.
  let params = {};

  //Need to output an error message for any other parameters passed beyond the list below. Right now, data is being
  //returned for invalid params such as t_units
  if ("all" in req.query) {
    // do nothing
  }
  else if (req.query.econ_id) {
    sql += " WHERE econs.id = ANY(:econ_id)";
    params["econ_id"] = larkin.parseMultipleIds(req.query.econ_id);
  }
  else if (req.query.econ) {
    sql += " WHERE econ = :econ";
    params["econ"] = req.query.econ;
  }
  else if (req.query.econ_type) {
    sql += " WHERE econ_type = :econ_type";
    params["econ_type"] = req.query.econ_type;
  }
  else if (req.query.econ_class) {
    sql += " WHERE econ_class = :econ_class";
    params["econ_class"] = req.query.econ_class;
  }

  sql += "\nGROUP BY econs.id ";
  if ("sample" in req.query) {
    sql += "\nLIMIT 5";
  }

  larkin.queryPg("burwell", sql, params, function (error, data) {
    console.log("CALLBACK DATA ", cb);
    if (error) {
      console.log("The error still returned from larkin")
      if (cb) {
        cb(error);
      } else if (error == "{\"success\":{\"v\":2,\"license\":\"CC-BY 4.0\",\"data\":[]}}") {
        console.log("THIS IS A SUCCESS JSON EVEN THOUGH IT'S CALLED ERROR", error)
        error = JSON.parse(error);
        res.status(200).json(error);
      } else {
        larkin.error(req, res, next, error);
      }
      return
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
