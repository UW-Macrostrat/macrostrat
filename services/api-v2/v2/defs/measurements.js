var api = require("../api"),
    larkin = require("../larkin");

module.exports = function(req, res, next) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }

  var sql = "SELECT measurements.id AS measure_id, measurement AS name, measurement_type AS type, measurement_class AS class, COUNT(DISTINCT unit_measures.unit_id) AS t_units FROM measurements LEFT JOIN measures ON measures.measurement_id = measurements.id LEFT JOIN unit_measures ON unit_measures.measuremeta_id = measures.measuremeta_id",
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
    sql += " WHERE measurements.id IN (:meas) ";
    params["meas"] = larkin.parseMultipleIds(req.query.measure_id);
  }

  sql += " GROUP BY measurements.id";

  if ("sample" in req.query) {
    sql += " LIMIT 5";
  }


  larkin.query(sql, params, function(error, data) {
    if (error) {
      return larkin.error(req, res, next, error);
    }

    larkin.sendData(data, res, ((api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json"), next);

  });

}
