var mysql = require("mysql"),
    pg = require("pg"),
    async = require("async"),
    credentials = require("./credentials"),
    csv = require("express-csv"),
    api = require("./api"),
    defs = require("./defs");

(function() {
  var larkin = {};

  larkin.connectMySQL = function() {
    // Non-blocking FTW
    this.pool = mysql.createPool(credentials.mysql);

    // Verify a connection has been made
    this.pool.getConnection(function(error, connection) {
      if (error) {
        throw new Error("Unable to connect to MySQL. Please check your credentials");
      };
    });

    this.pool.on("connection", function(connection) {
      // We could in theory take note of each query for analytics here...
      // Or set a session, etc...
    });
  };


  larkin.queryPg = function(db, sql, params, callback, send, res, format, next) {
    pg.connect("postgres://" + credentials.pg.user + "@" + credentials.pg.host + "/" + db, function(err, client, done) {
      if (err) {
        this.log("error", "error connecting - " + err);
        callback(err);
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
          "v": api.version,
          "data": data
        }
      });
    }
   };

   // Remove all whitespace from response
  larkin.sendCompact = function(data, res, format) {
    if (format === "csv") {
      res.csv(data, true);
    } else {
      res
        .set("Content-type", "application/json; charset=utf-8")
        .send(JSON.stringify({"success": {"v": api.version,"data": data}}, null, 0));
    }
  }

  larkin.sendBare = function(data, res, next) {
    res
      .set("Content-type", "application/json; charset=utf-8")
      .send(JSON.stringify(data, null, 0));
   };


  larkin.info = function(req, res, next) {
    this.defineRoute(req.route.path, function(definition) {
      res.json({
        "success": definition
      });
    });
  };


  larkin.error = function(req, res, next, message, code) {
    var responseMessage = (message) ? message : "Something went wrong. Please contact Shanan Peters.";
    if (code && code === 500 || code === 404) {
      res
        .status((code) ? code : 200)
        .json({
          "error": {
            "message": responseMessage
          }
        });
    } else {
      this.defineRoute(req.route.path, function(definition) {
        res
          .status((code) ? code : 200)
          .json({
            "error": {
              "v": api.version,
              "message": responseMessage,
              "about": definition
            }
          });
      });
    }
        
  };

  larkin.log = function(type, message) {
    console.log(type, message);
  };

  // Will return all field definitions
  larkin.defineFields = function(route, callback) {
    var routeDefs = {}
    async.each(defs[route].options.fields, function(field, callback) {
      if (defs.define.hasOwnProperty(field)) {
        routeDefs[field] = defs.define[field];
      } else {
        routeDefs[field] = ""
      }
      callback()
    }, function(error, result) {
      callback(routeDefs);
    });
  };

  // Get the metadata for a given route
  larkin.defineRoute = function(route, callback) {
    this.defineFields(route, function(fields) {
      var routeDefinition = {
        "v": api.version,
        "description": defs[route].description,
        "options": {
          "parameters": defs[route].options.parameters,
          "output_formats": defs[route].options.output_formats,
          "examples": defs[route].options.examples
        }
      };
      routeDefinition.options.fields = fields;
      callback(routeDefinition);
    }); 
  };


  larkin.getOutputFormat = function(requestedFormat) {
    switch (requestedFormat) {
      case "geojson_bare":
        return "geojson";
      case "topojson_bare":
        return "topojson";
      default:
        return (requestedFormat === "geojson" || requestedFormat === "topojson") ? requestedFormat : "geojson";
    }
  };

  module.exports = larkin;

}());
