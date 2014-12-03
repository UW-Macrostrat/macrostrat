var api = require("./api"),
    larkin = require("./larkin");

module.exports = function(req, res, next) {
  if (req.query.unit_id) {
    larkin.query("SELECT DISTINCT collection_no AS id, collection_name AS name FROM pbdb_matches WHERE unit_id = ? AND occs > 0 and release_date<NOW()", [req.query.unit_id], function(error, result) {
      if (error) {
        larkin.error(req, res, next, error);
      } else {
        larkin.sendData(result, res, "json", next);
      }
    });
  } else {
    larkin.info(req, res, next);
  }
}
