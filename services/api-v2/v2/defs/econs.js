var api = require("../api"),
    larkin = require("../larkin");

module.exports = function(req, res, next) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }

  var sql = "SELECT id AS econ_id, econ AS name, econ_type AS type, econ_class AS class, econ_color AS color FROM econs",
      params = {};

  if ("all" in req.query) {
    // do nothing
  } else if (req.query.econ_id) {
    sql += " WHERE id IN (:econ_ids)";
    params["econ_ids"] = larkin.parseMultipleIds(req.query.econ_id);

  } else if (req.query.econ){
    sql += " WHERE econ = :econ";
    params["econ"] = req.query.econ;

  } else if (req.query.econ_type){
    sql += " WHERE econ_type = :econ_type";
    params["econ_type"] = req.query.econ_type;

  } else if (req.query.econ_class){
    sql += " WHERE econ_class = :econ_class";
    params["econ_class"] = req.query.econ_class;
  }

  if ("sample" in req.query) {
    sql += " LIMIT 5";
  }

  var format = (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json";
  larkin.query(sql, params, null, true, res, format, next);
}
