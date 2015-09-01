var api = require("../api"),
    larkin = require("../larkin");

module.exports = function(req, res, next) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }

  var sql = "SELECT id AS environ_id, environ AS name, environ_type AS type, environ_class AS class, environ_color AS color FROM environs",
      environ = "";

  if (req.query.all) {
    // do nothing
  } else if (req.query.environ_class) {
    sql += " WHERE environ_class= ?";
    environ=req.query.environ_class;
  } else if (req.query.environ_type){
    sql += " WHERE environ_type = ?";
    environ = req.query.environ_type;
  } else if (req.query.environ){
    sql += " WHERE environ = ?";
    environ = req.query.environ;
  } else if (req.query.environ_id){
    sql += " WHERE id = ?";
    environ = req.query.environ_id;
  }

  if ("sample" in req.query) {
    sql += " LIMIT 5";
  }

  var format = (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json";
  larkin.query(sql, [environ], null, true, res, format, next);
}
