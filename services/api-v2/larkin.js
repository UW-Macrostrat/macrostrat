var mysql = require("mysql"),
    pg = require("pg"),
    async = require("async"),
    winston = require("winston"),
    credentials = require("./routes/credentials"),
    csv = require('express-csv'),
    Client = require('mariasql');

winston.add(winston.transports.File, { filename: "logs/larkin.log" });

(function() {
  var larkin = {};

  larkin.connectMySQL = function() {

    this.connection = new Client();
    this.connection.connect(credentials.mysql);

    this.connection.on('connect', function() {
      this.log("info", "Connected to MySQL");
    }.bind(this))
    .on('error', function(err) {
      this.log("error", err);
      this.connectMySQL();
    }.bind(this))
    .on('close', function(error) {
      this.log("error", error);
    });
  };

  larkin.queryPg = function(sql, params, callback, send, res, format, next) {
    pg.connect("postgres://" + credentials.pg.user + "@" + credentials.pg.host + "/" + credentials.pg.database, function(err, client, done) {
      if (err) {
        this.log("error", error);
      }
      client.query(sql, params, function(err, result) {
        done();

        if (err) {
          this.log("error", err);
        }

        if (send) {
          this.sendData(result, res, format, next);
        } else {
          callback(result);
        }
      }.bind(this));
    }.bind(this));
  }

  larkin.query = function(sql, params, callback, send, res, format, next) {
    this.connection.query(sql, params)
      .on("result", function(result) {
        result.results = [];
        result.on("row", function(row) {
          result.results.push(row);
        })
        .on("error", function(err) {
          callback(err);
          this.log("error", err);
        }.bind(this))
        .on("end", function(info) {
          callback(null, result.results);
        });
      })
      .on("end", function() {

      });
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


  larkin.error = function(res, next, message, options, code) {
    this.log("error", message);
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