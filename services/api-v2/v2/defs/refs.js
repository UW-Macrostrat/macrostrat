var api = require("../api"),
    larkin = require("../larkin");

module.exports = function(req, res, next) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }
  
  var sql = "SELECT id ref_id, pub_year, author, ref, doi, url FROM refs",
      params = {};

  if ("all" in req.query) {
    // do nothing
  } else if (req.query.ref_id) {
    sql += " WHERE id IN (:ref_id)";
    params["ref_id"] = larkin.parseMultipleIds(req.query.ref_id);

  } 

  if ("sample" in req.query) {
    sql += " LIMIT 5";
  }
  
  larkin.query(sql, params, null, true, res, ((api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json"), next);
}
