var api = require("./api"),
    larkin = require("./larkin");

module.exports = function(req, res, next) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }

  var sql = "SELECT intervals.id, interval_name, age_top late_age, age_bottom early_age FROM intervals",
      params = [];

  if (req.query.all) {
    // do nothing
  } else if (req.query.timescale){
    sql += " JOIN timescales_intervals ON interval_id=intervals.id JOIN timescales ON timescale_id=timescales.id WHERE timescale = ?";
    params.push(req.query.timescale);
  } else if (req.query.id && isFinite(req.query.id)){
    sql += " WHERE id ="+req.query.id;
  }
  
  sql += " ORDER BY late_age ASC";
  var format = (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json";

  larkin.query(sql, params, null, true, res, format, next);
}