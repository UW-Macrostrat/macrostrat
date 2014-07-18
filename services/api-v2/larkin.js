var mysql = require("mysql"),
    winston = require("winston"),
    credentials = require("./routes/credentials");

winston.add(winston.transports.File, { filename: "logs/larkin.log" });

(function() {
  var larkin = {};

  larkin.connectMySQL = function() {
    this.connection = mysql.createPool(credentials.credentials);

    this.connection.getConnection(function(error, connection) {
      if (error) {
        this.log("error", error);
      } else {
        this.log("info", "Connected to MySQL");
      }
    }.bind(this));
  };

  larkin.query = function(sql, params, callback, send, res, next) {
    this.connection.getConnection(function(err, connection) {
      connection.query(sql, params, function(error, result) {
        connection.release();
        if (error) {
          this.error(res, next, "Error retrieving from MySQL.", error);
        } else {
          if (send) {
            this.sendData(result, res, next);
          } else {
            callback(result);
          }
        }
      }.bind(this));
    }.bind(this));
  };

  larkin.sendData = function(data, res, next) {
    res.json({
      "success": {
        "results": data.length,
        "data": data
      }
    });
  };

  larkin.error = function(res, next, message, options, code) {
    //this.log("error", message);
    res.json((code) ? code : 200, {
      "error": {
        "message": message,
        "options": options
      }
    });
  };

  larkin.log = function(type, message) {
    winston.log(type, message);
  }

  module.exports = larkin;

}());