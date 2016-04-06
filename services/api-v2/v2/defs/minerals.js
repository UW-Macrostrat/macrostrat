var api = require("../api"),
    larkin = require("../larkin");

module.exports = function(req, res, next, cb) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }

  var sql = "SELECT minerals.id AS mineral_id, mineral AS mineral, min_type as mineral_type, formula AS formula, formula_tags AS formula_tags, url AS url FROM minerals";

  var params = {};

  if (req.query.mineral_id) {
    sql += " WHERE minerals.id = :mineral_id";
    params["mineral_id"] = req.query.mineral_id;
  } else if (req.query.mineral) {
    sql += " WHERE mineral = :mineral";
    params["mineral"] = req.query.mineral;
  } else if (req.query.mineral_type){
    sql += " WHERE min_type = :mineral_type";
    params["mineral_type"] = req.query.mineral_type;
  }

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
