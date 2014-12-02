var api = require("./api"),
    larkin = require("./larkin");

module.exports = function(req, res, next) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }
  var sql = "SELECT id,lith_att,att_type from lith_atts",
      lithatt = "";

  if (req.query.all) {
    // do nothing
  } else if (req.query.att_type) {
    sql += " WHERE att_type = ?"; 
    lithatt = req.query.att_type;
  } else if (req.query.lith_att){
    sql += " WHERE lith_att = ?"; 
    lithatt = req.query.lith_att;
  } else if (req.query.id){
    sql += " WHERE id = ?"; 
    lithatt = req.query.id;
  }

  var format = (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json";
  larkin.query(sql, [lithatt], null, true, res, format, next);
}
