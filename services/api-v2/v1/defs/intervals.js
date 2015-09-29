var api = require("../api"),
    larkin = require("../larkin");

module.exports = function(req, res, next) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }

  var sql = "SELECT intervals.id, interval_name AS name, interval_abbrev abbrev, age_top AS late_age, age_bottom AS early_age, interval_type AS type, interval_color AS color, GROUP_CONCAT(DISTINCT timescales.id SEPARATOR '|') AS timescale_id FROM intervals LEFT JOIN timescales_intervals ON interval_id=intervals.id LEFT JOIN timescales ON timescale_id=timescales.id ",
      params = [];

  var where = 0;

  if (req.query.all) {
    // do nothing
  } else {
    if (req.query.timescale) {
      sql += " WHERE timescale = ?";
      params.push(req.query.timescale);
      where ++;
    } else if (req.query.timescale_id) {
      sql += " WHERE timescales.id = ?";
      params.push(req.query.timescale_id);
      where ++;
    }

    if (req.query.id && isFinite(req.query.id)) {
      if (where < 1) {
        sql += " WHERE intervals.id = ?";
        params.push(req.query.id);
      } else {
        sql += " AND intervals.id = ?";
        params.push(req.query.id);
      }
      where++;
    } 

    if (req.query.late_age && req.query.early_age) {
      if (req.query.rule === "loose") {
        if (where < 1) {
          sql += " WHERE intervals.age_bottom >= ? AND intervals.age_top <= ?";
          params.push(req.query.late_age, req.query.early_age);
        } else {
          sql += " AND (intervals.age_bottom >= ? AND intervals.age_top <= ?)";
          params.push(req.query.late_age, req.query.early_age);
        }
      } else {
        if (where < 1) {
          sql += " WHERE intervals.age_top <= ? AND intervals.age_bottom >= ? OR intervals.age_top >= ? AND intervals.age_bottom <= ?";
          params.push(req.query.late_age, req.query.early_age, req.query.late_age, req.query.early_age);
        } else {
          sql += " AND ((intervals.age_top <= ? AND intervals.age_bottom >= ?) OR (intervals.age_top >= ? AND intervals.age_bottom <= ?))";
          params.push(req.query.late_age, req.query.early_age, req.query.late_age, req.query.early_age);
        }
      }
        
    } else if (req.query.age) {
      if (where < 1) {
        sql += " WHERE intervals.age_top <= ? AND intervals.age_bottom >= ?";
        params.push(req.query.age, req.query.age);
      } else {
        sql += " AND intervals.age_top <= ? AND intervals.age_bottom >= ?";
        params.push(req.query.age, req.query.age);
      }
    }
  }
  
  sql += " GROUP BY intervals.id ORDER BY late_age ASC";


  larkin.query(sql, params, function(error, result) {
    if (error) {
      console.log(error);
      return larkin.error(req, res, next, "Something went wrong");
    } else {
      if (req.query.format !== "csv") {
        result.forEach(function(d) {
          d.timescale_id = larkin.jsonifyPipes(d.timescale_id, "integers");
        });
      }

      larkin.sendData(result, res, (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json", next);
    }
  });

}
