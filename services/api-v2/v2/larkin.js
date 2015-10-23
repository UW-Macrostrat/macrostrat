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


  larkin.queryPg = function(db, sql, params, callback) {
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
            callback(null, result);
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

  larkin.query = function(sql, params, callback) {
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
          callback(null, result);
        }
      }.bind(this));
      //console.log(query.sql)
    }.bind(this));
  };


  larkin.sendData = function(req, res, next, options, outgoing) {
    if (options && options.format === "csv") {
      return res.csv(outgoing.data, true);
    }

    if (options && options.bare) {
      return res
        .set("Content-type", "application/json; charset=utf-8")
        .send(JSON.stringify(outgoing.data, null, 0));
    }

    if (options.refs) {
      larkin.getRefs(options.refs, outgoing.data, function(refs) {
        outgoing.refs = refs;
        larkin.finishSend(req, res, next, options, outgoing);
      });
    } else {
      larkin.finishSend(req, res, next, options, outgoing);
    }

  };

  larkin.finishSend = function(req, res, next, options, outgoing) {
    var responseObject = {
      "success": {
        "v": api.version,
        "license": api.license,
        "data": outgoing.data
      }
    }

    if (outgoing.refs) {
      responseObject.success["refs"] = outgoing.refs;
    }

    if ((options && options.compact) || outgoing.data.length <= 5) {
      return res
        .set("Content-type", "application/json; charset=utf-8")
        .send(JSON.stringify(responseObject, null, 0));
    }

    return res.json(responseObject);
  }


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
      data = data.split("|").filter(function(d) {
        if (d) {
          return d
        }
      });
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


  larkin.getRefs = function(key, data, callback) {

    // Get unique ref_ids
    var ref_ids = _.uniq(
        _.flatten(
          data.map(function(d) {
            return d[key]
          }
        )
      )
    );

    if (key === "refs" || key === "ref_id") {
      larkin.query("SELECT refs.id AS ref_id, pub_year, author, ref, doi, url, COUNT(DISTINCT units_sections.unit_id) AS t_units FROM refs LEFT JOIN col_refs ON col_refs.ref_id = refs.id LEFT JOIN units_sections ON units_sections.col_id = col_refs.col_id WHERE refs.id IN (:ref_id) GROUP BY refs.id", {"ref_id": ref_ids}, function(error, data) {
        var refs = {}
        data.forEach(function(d) {
          refs[d[key]] = d.author + ". " + d.ref + ". " + d.pub_year + ". " + (d.doi + ". " || "") + (d.url  + "." || "");
        });

        callback(refs);
      });
    } else {
      larkin.queryPg("burwell", "SELECT source_id, name, COALESCE(url, '') url, COALESCE(ref_title, '') ref_title, COALESCE(authors, '') authors, COALESCE(ref_year, '') ref_year, COALESCE(ref_source, '') ref_source, COALESCE(isbn_doi, '') isbn_doi FROM maps.sources WHERE source_id = ANY($1)", [ref_ids], function(error, result) {
        var refs = {}
        result.rows.forEach(function(d) {
          refs[d[key]] = d.authors + ". " + d.ref_title + ". " + d.ref_year + ". " + (d.isbn_doi + ". " || "") + (d.ref_source  + "." || "");
        });

        callback(refs);
      });
    }


  }

  module.exports = larkin;

}());
