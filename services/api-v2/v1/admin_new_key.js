var uuid = require("node-uuid"),
    validator = require("validator"),
    api = require("./api"),
    larkin = require("./larkin");


module.exports = function(req, res, next) {
  if (Object.keys(req.query).length < 1) {
    //return larkin.info(req, res, next);
    return larkin.error(req, res, next, "email, first_name, last_name, permissions, and admin key required");
  }

  // Verify we have all of our fields
  ["email", "first_name", "last_name", "permissions", "key"].forEach(function(d) {
    if (!req.query[d] || req.query[d].length < 2) {
      return larkin.error(req, res, next, "email, first_name, last_name, permissions, and admin key required");
    }
  });

  if (!validator.isEmail(req.query.email)) {
    return larkin.error(req, res, next, "Invalid email supplied");
  }
  if (!validator.isUUID(req.query.key)) {
    return larkin.error(req, res, next, "Invalid API key supplied");
  }

  // Make sure this email, first_name, last_name combo doesn't exist
  larkin.queryPg("geomacro", "SELECT * FROM apikeys WHERE email = $1 AND first_name = $2 AND last_name = $3", [req.query.email, req.query.first_name, req.query.last_name], function(error, data) {
    if (error) {
      larkin.error(req, res, next, "Something went wrong");
    } else {
      if (data.rows && data.rows.length > 0) {
        larkin.error(req, res, next, "This person already has an API key.");
      } else {

        // Verify that the provided key is legit
        larkin.queryPg("geomacro", "SELECT * FROM apikeys WHERE key = $1 AND admin is TRUE", [req.query.key], function(error, data) {
          if (error) {

          } else {
            if (data.rows && data.rows.length > 0) {
              var newKey = uuid.v4(),
                  permissions = req.query.permissions.split(",");

              larkin.queryPg("geomacro", "INSERT INTO apikeys (key, email, first_name, last_name, permissions) VALUES ($1, $2, $3, $4, $5)", [newKey, req.query.email, req.query.first_name, req.query.last_name, permissions], function(error, result) {
                if (error) {
                  larkin.error(req, res, next, "Something went wrong");
                } else {
                  larkin.sendData({"new_key": newKey}, res, "json");
                }
              });

            } else {
              larkin.error(req, res, next, "Invalid admin API key.");
            }
          }
        });   
      }
    }
  });   
}
