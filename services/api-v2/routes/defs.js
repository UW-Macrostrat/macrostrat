(function() {
  var async = require("async");

  var defs = {};

  // Instead of adding metadata to each route in api.js, we are going to do it here
  defs["/column"] = {
    "description": "Gets all attributes of a given column",
    "options": {
      "parameters": {
        "id": "Get a column by id",
        "lat": "A valid latitude",
        "lng": "A valid longitude",
        "response": "Can be 'short' or 'long'"
      },
      "output_formats": "json",
      "examples": ["api/columns?id=17", "api/columns?lat=50&lng=-80"],
      "fields": {
        "short": [
          "id",
          "strat_name",
          "Mbr",
          "Fm",
          "Gp",
          "SGp",
          "era",
          "period",
          "max_thick",
          "min_thick",
          "color",
          "lith_type",
          "pbdb"
        ],
        "long": [
          "FO_interval",
          "FO_h",
          "FO_age",
          "b_age",
          "LO_interval",
          "LO_h",
          "LO_age",
          "t_age",
          "position_bottom",
          "notes"
        ]
      }
    }
  };

  // This is the primary dictionary for all field definitions
  defs.define = {
    "id": "An id",
    "strat_name": "Strat name"
  };

  // Given a route and field type(optional), will return all field definitions
  defs.defineRoute = function(route, type) {
    var routeDefs = {}
    async.each(this[route].options.fields[ (type) ? type : "short" ], function(field, callback) {
      routeDefs[field] = defs.define[field];
      callback()
    }, function(error) {
      return routeDefs;
    });
    return routeDefs;
  };

  module.exports = defs;
}());
