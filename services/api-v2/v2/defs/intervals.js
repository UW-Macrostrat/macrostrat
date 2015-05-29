var api = require("../api"),
    larkin = require("../larkin");

module.exports = function(req, res, next) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }

  var sql = "SELECT intervals.id AS int_id, interval_name AS name, interval_abbrev abbrev, age_top AS t_age, age_bottom AS b_age, interval_type AS type, interval_color AS color, GROUP_CONCAT(DISTINCT timescales.id SEPARATOR '|') AS timescale_id FROM intervals JOIN timescales_intervals ON interval_id=intervals.id JOIN timescales ON timescale_id=timescales.id ";
  
  var params = {},
      where = [];

  if (req.query.timescale) {
    where.push(" timescale = :timescale");
    params["timescale"] = req.query.timescale;

  } else if (req.query.timescale_id) {
    where.push("timescales.id IN (:timescale_id)");
    params["timescale_id"] = larkin.parseMultipleIds(req.query.timescale_id);
  }

  if (req.query.int_id && isFinite(req.query.int_id)) {
    where.push("intervals.id IN (:int_id)");
    params["int_id"] = larkin.parseMultipleIds(req.query.int_id);
  } 

  if (req.query.b_age && req.query.t_age) {
    if (req.query.rule === "loose") {
      where.push("intervals.age_bottom >= :b_age AND intervals.age_top <= t_age");
      params["b_age"] = req.query.b_age;
      params["t_age"] = req.query.t_age;

    } else {
      where.push("((intervals.age_top <= :t_age AND intervals.age_bottom >= :b_age) OR (intervals.age_top >= :t_age AND intervals.age_bottom <= :b_age))");
      params["b_age"] = req.query.b_age;
      params["t_age"] = req.query.t_age;
    }
      
  } else if (req.query.age) {
    where.push("intervals.age_top <= :age AND intervals.age_bottom >= :age");
    params["age"] = req.query.age;
  }
  
  if (where.length > 0) {
    sql += ("WHERE " + where.join(" AND "));
  }

  sql += " GROUP BY intervals.id ORDER BY t_age ASC";


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
