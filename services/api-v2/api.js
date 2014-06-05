var mysql = require("mysql"),
    winston = require("winston"),
    credentials = require("./routes/credentials");

winston.add(winston.transports.File, { filename: "logs/larkin.log" });

(function() {
  var api = {};

  api.connectMySQL = function() {
    this.connection = mysql.createPool(credentials.credentials);

    this.connection.getConnection(function(error, connection) {
      if (error) {
        winston.log("error", error);
      } else {
        winston.log("info", "Connected to MySQL");
      }
    });
  };

  api.query = function(sql, params, res, next) {
    var root = this;

    this.connection.getConnection(function(err, connection) {
      connection.query(sql, params, function(error, result) {
        connection.release();
        if (error) {
          root.error(res, next, "Error retrieving from MySQL.", error);
        } else {
          root.sendData(result, res, next);
        }
      });
    });
  };

  api.intermediateQuery = function(sql, params, callback) {
    var root = this;

    this.connection.getConnection(function(err, connection) {
      connection.query(sql, params, function(error, result) {
        connection.release();
        if (error) {
          root.error(res, next, "Error retrieving from MySQL.", error);
        } else {
          callback(result);
        }
      });
    });
  };

  api.sendData = function(data, res, next) {
    res.json({
      "success": {
        "results": data.length,
        "data": data
      }
    });
  };

  api.error = function(res, next, message, options, code) {
    res.json((code) ? code : 200, {
      "error": {
        "message": message,
        "options": options
      }
    });
  };

  api.log = function(type, message) {
    winston.log(type, message);
  }

  module.exports = api;

}());