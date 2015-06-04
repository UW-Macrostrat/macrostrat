var http = require("http"),
    async = require("async"),
    fs = require("fs"),
    defs = require("../defs");

function getResponseTypes(routePath, callback) {
  http.get("http://localhost:5000/api/v2" + routePath, function(response) {
    var body = "";
    response.on("data", function(d) {
      body += d;
    });

    response.on("end", function() {
      var data = JSON.parse(body);

      if (data.success.options && data.success.options.response_types) {
        callback(true)
      } else {
        callback(false);
      }
    });
  });
}

function getSample(routePath, callback) {
  var url = "http://localhost:5000/api/v2" + routePath + "?sample";
  getResponseTypes(routePath, function(longResponse) {
    if (longResponse) {
      url += "&response=long";
    }

    http.get(url, function(response) {
      var body = "";
      response.on("data", function(d) {
        body += d;
      });

      response.on("end", function() {
        var data = JSON.parse(body);

        if (data.success.data && data.success.data.features) {
          defs[routePath].options.fields = Object.keys(data.success.data.features[0].properties);
        } else if (data.success.data) {
          defs[routePath].options.fields = Object.keys(data.success.data[0]);
        }

        if (defs[routePath].options && defs[routePath].options.fields) {
          defs[routePath].options.fields.forEach(function(d) {
            if (!(d in defs.define)) {
              console.log(d, " missing from dictionary (" + routePath + ")");
            }
          });
        }

        callback(null);
      });
    });

  });
  
}

var allFields = [];

http.get("http://localhost:5000/api/v2", function(response) {
  var body = "";
  response.on("data", function(d) {
    body += d;
  });

  response.on("end", function() {
    var data = JSON.parse(body);

    async.each(Object.keys(data.success.routes), getSample, function(error) {
      fs.writeFile("./defs.js", "(function() { \n  var defs = " + JSON.stringify(defs, null, 2) + "; \n  module.exports = defs; \n}());", function(error) {
        if (error) {
          return console.log(error);
        }

        console.log("\nNew route output fields saved!");
      })
    });

  });
});
