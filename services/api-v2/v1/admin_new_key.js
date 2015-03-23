var uuid = require("node-uuid"),
    validator = require("validator"),
    api = require("./api"),
    async = require("async"),
    larkin = require("./larkin");


module.exports = function(req, res, next) {
  async.waterfall([
    function(callback) {
      if (Object.keys(req.query).length < 1) {
        callback("email, first_name, last_name, permissions, and admin key required");
      } else {
        callback(null);
      }
    },

    function(callback) {
      // Verify we have all of our fields
      ["email", "first_name", "last_name", "permissions", "key"].forEach(function(d) {
        if (!req.query[d] || req.query[d].length < 2) {
          callback("email, first_name, last_name, permissions, and admin key required");
        }
      });
      callback(null);
    },

    function(callback) {
      // Make sure the email is valid
      if (!validator.isEmail(req.query.email)) {
        callback("Invalid email supplied");
      } else {
        callback(null);
      }
    },

    function(callback) {
      // Make sure this email, first_name, last_name combo doesn't exist
      larkin.queryPg("geomacro", "SELECT * FROM apikeys WHERE email = $1 AND first_name = $2 AND last_name = $3", [req.query.email, req.query.first_name, req.query.last_name], function(error, data) {
        if (error) {
          callback("something went wrong");
        } else if (data.rows && data.rows.length > 0) {
            callback("This person already has an API key.");
        } else {
          callback(null);
        }
      });
    },

    function(callback) {
      // Verify that to provided key is valid and an admin key
      larkin.verifyKey(req.query.key, function(error, validated) {
        if (error) {
          callback(error);
        } else if (!validated.valid || !validated.info.admin) {
            callback("Invalid API key supplied");
        } else {
          callback(null);
        }
      });
    },

    function(callback) {
      // Add the new user to the database
      var newKey = uuid.v4(),
          permissions = req.query.permissions.split(",");

      larkin.queryPg("geomacro", "INSERT INTO apikeys (key, email, first_name, last_name, permissions) VALUES ($1, $2, $3, $4, $5)", [newKey, req.query.email, req.query.first_name, req.query.last_name, permissions], function(error, result) {
        if (error) {
          callback("Something went wrong");
        } else {
          callback(null, newKey);
        }
      });
    }

  ], function(error, result) {
    if (error) {
      larkin.error(req, res, next, error);
    } else {
      // Return the new key
      larkin.sendData({"new_key": result}, res, "json");
    }
  });
}
