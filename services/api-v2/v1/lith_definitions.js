var api = require("./api"),
    larkin = require("./larkin");

module.exports = function(req, res, next) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }

  var sql = "SELECT id,lith,lith_type,lith_class,lith_color from liths",
      lith = "";

  if (req.query.all) {
    // do nothing
  } else if (req.query.lith_class) {
    sql += " WHERE lith_class = ?";  
    lith = req.query.lith_class;
  } else if (req.query.lith_type){
    sql += " WHERE lith_type = ?"; 
    lith = req.query.lith_type;
  }  else if (req.query.lith){
    sql += " WHERE lith = ? "; 
    lith = req.query.lith;
  }  else if (req.query.id){
    sql += " WHERE id = ? "; 
    lith = req.query.id;
  }

  var format = (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json";
  larkin.query(sql, [lith], null, true, res, format, next);
  
}