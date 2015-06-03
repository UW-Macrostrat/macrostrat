var api = require("../api"),
    larkin = require("../larkin");

module.exports = function(req, res, next) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }

  var sql = "SELECT id AS lith_id, lith, lith_type, lith_class, lith_color FROM liths",
      params = {};

  if (req.query.lith_class) {
    sql += " WHERE lith_class = :lith_class"; 
    params["lith_class"] = req.query.lith_class; 
  } else if (req.query.lith_type){
    sql += " WHERE lith_type = :lith_type"; 
    params["lith_type"] = req.query.lith_type;
  }  else if (req.query.lith){
    sql += " WHERE lith = :lith ";
    params["lith"] = req.query.lith; 
  }  else if (req.query.lith_id){
    sql += " WHERE id IN (:lith_id)";
    params["lith_id"] = larkin.parseMultipleIds(req.query.lith_id); 
  }

  if ("sample" in req.query) {
    sql += " LIMIT 5";
  }

  larkin.query(sql, params, null, true, res, ((api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json"), next);
  
}
