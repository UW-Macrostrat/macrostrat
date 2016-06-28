var api = require("../api"),
    larkin = require("../larkin");

module.exports = function(req, res, next, cb) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }

  var sql = "SELECT structures.id AS structure_id, structure AS name, structure_type AS structure_type, COALESCE(structure_group, '') AS `group`, structure_class AS `class` FROM structures",
      params = {};

  if (req.query.structure_class) {
    sql += " WHERE structure_class = :structure_class";
    params["structure_class"] = req.query.structure_class;
  } else if (req.query.structure_type){
    sql += " WHERE structure_type = :structure_type";
    params["structure_type"] = req.query.structure_type;
  }  else if (req.query.structure){
    sql += " WHERE structure = :structure ";
    params["structure"] = req.query.structure;
  }  else if (req.query.structure_id){
    sql += " WHERE structures.id IN (:structure_id)";
    params["structure_id"] = larkin.parseMultipleIds(req.query.structure_id);
  } else if (req.query.structure_like){
    sql += " WHERE structure LIKE :structure";
    params["structure"] = '%' + req.query.structure_like + '%';
  }

  sql += " GROUP BY structure.id ";

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
        bare: (api.acceptedFormats.bare[req.query.format]) ? true : false,
        compact: true
      }, {
        data: data
      });
    }


  });
}
