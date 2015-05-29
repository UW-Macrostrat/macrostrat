var api = require("../api"),
    larkin = require("../larkin");

module.exports = function(req, res, next) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }

  var sql = "SELECT id AS measure_id, measurement_class, measurement_type, measurement FROM measurements",
      params = {};

  if (req.query.all) {
    // do nothing
  } else if (req.query.measurement_class) {
    sql += " WHERE measurement_class = :meas";
    params["meas"] = req.query.measurement_class;
  } else if (req.query.measurement_type){
    sql += " WHERE measurement_type = :meas"; 
    params["meas"] = req.query.measurement_type;

  }  else if (req.query.measurement){
    sql += " WHERE measurement = :meas";
    params["meas"] = req.query.measurement;

  }  else if (req.query.measure_id){
    sql += " WHERE id IN (:meas) "; 
    params["meas"] = larkin.parseMultipleIds(req.query.measure_id);
  }

  var format = (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json";
  larkin.query(sql, params, null, true, res, format, next);
  
}
