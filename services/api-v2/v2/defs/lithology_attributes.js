var api = require("../api"),
    larkin = require("../larkin");

module.exports = function(req, res, next) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }

  var sql = "SELECT lith_atts.id AS lith_att_id, lith_att AS name, att_type AS type, COUNT(DISTINCT unit_liths.unit_id) AS t_units FROM lith_atts LEFT JOIN unit_liths_atts ON unit_liths_atts.lith_att_id = lith_atts.id LEFT JOIN unit_liths ON unit_liths_atts.unit_lith_id = unit_liths.id ",
      params = {};

  if (req.query.att_type) {
    sql += " WHERE att_type = :att_type";
    params["att_type"] = req.query.att_type;
  } else if (req.query.lith_att) {
    sql += " WHERE lith_att = :lith_att";
    params["lith_att"] = req.query.lith_att;
  } else if (req.query.lith_att_id) {
    sql += " WHERE lith_atts.id IN (:lith_att_id)";
    params["lith_att_id"] = larkin.parseMultipleIds(req.query.lith_att_id);
  }

  sql += " GROUP BY lith_atts.id";

  if ("sample" in req.query) {
    sql += " LIMIT 5";
  }

  larkin.query(sql, params, null, true, res, ((api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json"), next);
}
