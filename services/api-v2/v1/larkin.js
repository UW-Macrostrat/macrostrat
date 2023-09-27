var mysql = require("mysql"),
    pg = require("pg"),
    async = require("async"),
    credentials = require("./credentials"),
    csv = require("csv-express"),
    api = require("./api"),
    defs = require("./defs"),
    validator = require("validator");

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


  larkin.queryPg = function (db, sql, params, callback, send, res, format, next) {

    const nameMapping = credentials.postgresDatabases ?? {}
    const dbName = nameMapping[db] ?? db

    const pool = new pg.Pool({connectionString: credentials.pg.connectionString});

    pool.connect(function(err, client, done) {
      if (err) {
        this.log("error", "error connecting - " + err);
        callback(err);
      } else {
        var query = client.query(sql, params, function(err, result) {
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
       // console.log(query);
      }
    }.bind(this));
  };


  larkin.query = function(sql, params, callback, send, res, format, next) {
    this.pool.getConnection(function(err, connection) {
      var query = connection.query(sql, params, function(error, result) {
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
      //console.log(query.sql)
    }.bind(this));
  };


  larkin.sendData = function(data, res, format, next) {
    if (format === "csv") {
      res.csv(data, true)
    } else {
      if (data.length > 5) {
        res
          .set("Content-type", "application/json; charset=utf-8")
          .send(JSON.stringify({"success": {"v": api.version,"data": data}}, null, 0));
        } else {
          res.json({
            "success": {
              "v": api.version,
              "data": data
            }
          });
        }
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
  };


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
      if (defs[route].options.response_types) {
        routeDefinition.options.response_types = defs[route].options.response_types;
      }
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


  larkin.jsonifyPipes = function(data, type) {
    if (data) {
      data = data.split("|");
      if (type === "integers") {
        data = data.map(function(d) {
          return parseInt(d);
        });
      } else if (type === "floats") {
        data = data.map(function(d) {
          return parseFloat(d);
        });
      }

      return data;

    } else {
      return [];
    }
  };


  larkin.verifyKey = function(key, callback) {
    if (!validator.isUUID(key)) {
      callback("Invalid key", null);
    } else {
      this.queryPg("geomacro", "SELECT key, admin FROM apikeys WHERE key = $1", [key], function(error, data) {
        if (error) {
          callback("Internal issue", null);
        } else if (data.rows && data.rows.length === 1) {
          callback(null, {"valid": true, "info": data.rows[0]});
        } else {
          callback(null, {"valid": false});
        }
      });
    }
  };


  larkin.parseMultipleIds = function(requested_ids) {
    var ids = requested_ids.split(","),
              placeholders = [];

    ids = ids.map(function(d) {
      return parseInt(d);
    });

    for (var i = 0; i < ids.length; i++) {
      placeholders.push("?");
    }

    return {
      ids: ids,
      placeholders: placeholders
    }
  };


  module.exports = larkin;

}());
