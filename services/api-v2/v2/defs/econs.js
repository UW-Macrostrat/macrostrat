var api = require("../api"),
    larkin = require("../larkin");

module.exports = function(req, res, next) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }
  
  var sql = "SELECT id AS econ_id, econ, econ_type, econ_class FROM econs",
      params = [];

  if ("all" in req.query) {
    // do nothing
  } else if (req.query.econ_id) {
    sql += " WHERE id = ?";
    params.push(req.query.econ_id);

  } else if (req.query.econ){
    sql += " WHERE econ = ?";
    params.push(req.query.econ);

  } else if (req.query.econ_type){
    sql += " WHERE econ_type = ?";
    params.push(req.query.econ_type);

  } else if (req.query.econ_class){
    sql += " WHERE econ_class = ?";
    params.push(req.query.econ_class);
  }

  var format = (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json";
  larkin.query(sql, params, null, true, res, format, next);
}
