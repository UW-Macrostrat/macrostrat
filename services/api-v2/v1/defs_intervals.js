var api = require("./api"),
    larkin = require("./larkin");

module.exports = function(req, res, next) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }

  var sql = "SELECT intervals.id, interval_name AS name, age_top AS late_age, age_bottom AS early_age, interval_type AS type, interval_color AS color FROM intervals",
      params = [];

  var where = 0;
  if (req.query.all) {
    // do nothing
  } else {
    if (req.query.timescale) {
      sql += " JOIN timescales_intervals ON interval_id=intervals.id JOIN timescales ON timescale_id=timescales.id WHERE timescale = ?";
      params.push(req.query.timescale);
      where ++;
    } 
    if (req.query.id && isFinite(req.query.id)) {
      if (where < 1) {
        sql += " WHERE id = ?";
        params.push(req.query.id);
      } else {
        sql += " AND id = ?";
        params.push(req.query.id);
      }
      where++;
    } 
    if (req.query.late_age && req.query.early_age) {
      if (where < 1) {
        sql += " WHERE age_top <= ? AND age_bottom >= ? OR age_top >= ? AND age_bottom <= ?";
        params.push(req.query.late_age, req.query.early_age, req.query.late_age, req.query.early_age);
      } else {
        sql += " AND ((age_top <= ? AND age_bottom >= ?) OR (age_top >= ? AND age_bottom <= ?))";
        params.push(req.query.late_age, req.query.early_age, req.query.late_age, req.query.early_age);
      }
    } else if (req.query.age) {
      if (where < 1) {
        sql += " WHERE age_top <= ? AND age_bottom >= ?";
        params.push(req.query.age, req.query.age);
      } else {
        sql += " AND age_top <= ? AND age_bottom >= ?";
        params.push(req.query.age, req.query.age);
      }
    }
  }
  
  sql += " ORDER BY late_age ASC";
  var format = (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json";

  larkin.query(sql, params, null, true, res, format, next);
}
