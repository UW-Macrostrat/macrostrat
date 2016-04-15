var api = require("../api"),
    larkin = require("../larkin");

module.exports = function(req, res, next, cb) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }

  var sql = "SELECT liths.id AS lith_id, lith AS name, lith_type AS type, lith_class AS class, lith_color AS color, COUNT(distinct units_sections.unit_id) AS t_units FROM liths LEFT JOIN unit_liths ON unit_liths.lith_id = liths.id LEFT JOIN units_sections ON units_sections.unit_id = unit_liths.unit_id ",
      params = {};

  if (req.query.lith_class) {
    sql += " WHERE lith_class = :lith_class";
    params["lith_class"] = req.query.lith_class;
  } else if (req.query.lith_type){
    sql += " WHERE lith_type = :lith_type";
    params["lith_type"] = req.query.lith_type;
  }  else if (req.query.lith){
    sql += " WHERE lith = :lith ";
    params["lith"] = req.query.lith;
  }  else if (req.query.lith_id){
    sql += " WHERE liths.id IN (:lith_id)";
    params["lith_id"] = larkin.parseMultipleIds(req.query.lith_id);
  } else if (req.query.lith_like){
    sql += " WHERE lith LIKE :lith";
    params["lith"] = req.query.lith_like + '%';
  }

  sql += " GROUP BY liths.id ";

  if ("sample" in req.query) {
    sql += " LIMIT 5";
  }

  larkin.query(sql, params, function(error, data) {
    if (error) {
      if (cb) {
        cb(error);
      } else {
        return larkin.error(req, res, next, error);
      }
    }

    if (cb) {
      cb(null, data);
    } else {
      larkin.sendData(req, res, next, {
        format: (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json",
        bare: (api.acceptedFormats.bare[req.query.format]) ? true : false
      }, {
        data: data
      });
    }


  });
}
