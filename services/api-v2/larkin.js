var mysql = require("mysql"),
    pg = require("pg"),
    async = require("async"),
    winston = require("winston"),
    credentials = require("./routes/credentials"),
    csv = require('express-csv');

(function() {
  var larkin = {};

  larkin.connectMySQL = function() {
    // Non-blocking FTW
    this.pool = mysql.createPool(credentials.mysql);

    this.pool.on("connection", function(connection) {
      // We could in theory take note of each query for analytics here...
      // Or set a session, etc...
    });
  };


  larkin.queryPg = function(db, sql, params, callback, send, res, format, next) {
    pg.connect("postgres://" + credentials.pg.user + "@" + credentials.pg.host + "/" + db, function(err, client, done) {
      if (err) {
        this.log("error", "error connecting - " + err);
        callback(error);
      } else {
        client.query(sql, params, function(err, result) {
          done();
          if (err) {
            this.log("error", err);
            callback(err);
          } else {
            if (send) {
              this.sendData(result, res, format, next);
            } else {
              callback(null, result);
            }
          }

        }.bind(this));
      }
    }.bind(this));
  };


  larkin.query = function(sql, params, callback, send, res, format, next) {
    this.pool.getConnection(function(err, connection) {
      connection.query(sql, params, function(error, result) {
        // Remove the connection
        connection.destroy();
        if (error) {
          if (callback) {
            callback(error);
          } else {
            this.error(res, next, "Error retrieving from MySQL.", error);
          }
        } else {
          if (send) {
            this.sendData(result, res, format, next);
          } else {
            callback(null, result);
          }
        }
      }.bind(this));
    }.bind(this));
  };


  larkin.sendData = function(data, res, format, next) {
    if (format === "csv") {
      res.csv(data, true)
    } else {
      res.json({
        "success": {
        "results": data.length,
        "data": data
        }
      });
    }
   };


  larkin.info = function(req, res, next) {
    res.json({
      "success": req.route.meta
    });
  };


  larkin.error = function(res, next, message, options, code) {
    var responseMessage = (message) ? message : "Something went wrong. Please contact Shanan Peters.";
    res
      .status((code) ? code : 200)
      .json({
        "error": {
          "message": responseMessage,
          "about": options
        }
      });
  };

  larkin.log = function(type, message) {
    winston.log(type, message);
  };

  module.exports = larkin;

}());
