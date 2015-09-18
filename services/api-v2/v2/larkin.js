var mysql = require("mysql"),
    pg = require("pg"),
    async = require("async"),
    _ = require("underscore"),
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
  };


  larkin.queryPg = function(db, sql, params, callback, send, res, format, next) {
    pg.connect("postgres://" + credentials.pg.user + "@" + credentials.pg.host + "/" + db, function(err, client, done) {
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
        //console.log(query.text, query.values);
      }
    }.bind(this));
  };

  larkin.toUnnamed = function(sql, params) {
    var placeholders = sql.match(/(?:\?)|(?::(\d+|(?::?[a-zA-Z][a-zA-Z0-9_]*)))/g),
        newParams = [];

    for (var i = 0; i < placeholders.length; i++) {
      var flag = (placeholders[i].substr(0, 2) === "::") ? "::" : ":",
          sub = (flag === "::") ? "??" : "?";

      sql = sql.replace(placeholders[i], sub);
      newParams.push(params[placeholders[i].replace(flag, "")]);
    }

    return [sql, newParams];
  };

  larkin.query = function(sql, params, callback, send, res, format, next) {
    // See if the query is using :named_parameters or positional ?
    if (sql.indexOf(':') > -1) {
      var newQuery = larkin.toUnnamed(sql, params);
      sql = newQuery[0];
      params = newQuery[1];
    }

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
          .send(JSON.stringify({"success": {"v": api.version,"license": api.license,"data": data}}, null, 0));
        } else {
          res.json({
            "success": {
              "v": api.version,
              "license": api.license,
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
        .send(JSON.stringify({"success": {"v": api.version,"license": api.license,"data": data}}, null, 0));
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
              "license": api.license,
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
        "license": api.license,
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
        return data.map(function(d) {
          return parseInt(d);
        });
      } else if (type === "floats") {
        return data.map(function(d) {
          return parseFloat(d);
        });
      } else if (type === "strings") {
        return data
      } else {
        return data;
      }

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
    return requested_ids.split(",").map(function(d) {
      return parseInt(d);
    });
  };

  larkin.parseMultipleStrings = function(text) {
    return text.split(",").map(function(d) {
      return d;
    });
  };


  larkin.findNumberInString = function(obj){
    var matches = obj.replace(/,/g, '').match(/(\+|-)?((\d+(\.\d+)?)|(\.\d+))/);
    return matches && matches[0] || null;
  };

  larkin.fixLiths = function(obj) {
    return obj.split("|").map(function(d) {
      var prop = parseFloat(this.findNumberInString(d)),
          type = d.replace(prop, "").replace(/\.\d+/, "").replace("0", "").replace("00", "").trim();

      // WTF? No idea why this is necessary...
      type = type.replace("0", "");
      type = type.trim()

      return {"type": type, "prop": prop}

    }.bind(this));
  };

  larkin.pipifyLiths = function(data) {
    return data.map(function(d) {
      return d.type + " ~ " + d.prop;
    }).join("|");
  };

  // Handle lith_atts
  larkin.pipifyAttrs = function(data) {
    return data.map(function(attr) {
      return ((attr.atts) ? (attr.atts.join(" ") + " ") : "") +
              attr.name + " " + attr.type + " " + attr.class + " " +
             ((attr.prop) ? " ~ " + attr.prop : "");
    }).join("|");
  };

  larkin.summarizeAttribute = function(data, type) {
    var mommaCat = _.flatten(
      data.map(function(d) {
        return d[type];
      })).filter(function(d) {
        if (d) { return d }
      });

    if (mommaCat.length < 1) {
      return [];
    }

    var cats = _.groupBy(mommaCat, function(d) { return d[type + "_id"] }),
        total_cats = Object.keys(cats).map(function(cat) { return cats[cat].length }).reduce(function(a, b) { return a + b }, 0),
        parsedCats = [];

    Object.keys(cats).forEach(function(d) {
      if (type === "lith") {
        var prop = parseFloat((
          cats[d].map(function(j) {
            return j.prop
          }).reduce(function(a, b) {
            return a + b
          }, 0)/data.length
        ).toFixed(4));

      } else {
        var prop = parseFloat((cats[d].length/total_cats).toFixed(4));
      }

      var kitten = {
        "name": cats[d][0].name,
        "type": cats[d][0].type,
        "class": cats[d][0].class,
        "prop": prop
      }
      kitten[type + "_id"] = parseInt(d);
      parsedCats.push(kitten);

    });

    return parsedCats;
  };

  larkin.normalizeLng = function(lng) {
    // via https://github.com/Leaflet/Leaflet/blob/32c9156cb1d1c9bd53130639ec4d8575fbeef5a6/src/core/Util.js#L87
    return ((lng - 180) % 360 + 360) % 360 - 180;
  }


  module.exports = larkin;

}());
