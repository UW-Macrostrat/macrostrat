var api = require("./api"),
    larkin = require("./larkin");


module.exports = function(req, res, next) {
  if (Object.keys(req.query).length < 1 || !req.query.key) {
    //return larkin.info(req, res, next);
    return larkin.error(req, res, next, "Valid API key required");
  }

  // Make sure this email, first_name, last_name combo doesn't exist
  larkin.queryPg("geomacro", "SELECT * FROM apikeys WHERE key = $1", [req.query.key], function(error, data) {
    if (error) {
      larkin.error(req, res, next, "Something went wrong");
    } else {
      larkin.sendData(data.rows, res, "json");
    }
  });   
}
