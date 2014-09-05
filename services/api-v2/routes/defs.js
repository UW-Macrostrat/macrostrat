(function() {
  var async = require("async");

  var defs = {};

  // Instead of adding metadata to each route in api.js, we are going to do it here
  defs["/column"] = {
    "description": "Get all units of a given column, optionally with geometry",
    "options": {
      "parameters": {
        "id": "integer, get a column by unique identifier",
        "lat": "nuumber, decimal degree latitude, WGS84",
        "lng": "number, decimal degree longitude, WGS84",
        "geom": "boolean, whether associated geometry is returned",
        "response": "Can be 'short' or 'long'"
      },
      "output_formats": "json",
      "examples": ["?id=17", "?lat=50&lng=-80"],
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
          "pbdb",
          "geom"
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
          "notes",
        ]
      }
    }
  };
  
  defs["/columns"] = {
    "description": "Get all colums containing one or more units matching specfied search criteria",
    "options": {
      "parameters": {
        "interval_name": "text, name of search time interval",
        "age": "number, search age in Myr before present",
        "age_top": "number, youngest limit of search, in Myr before present - must be used with age_bottom",
        "age_bottom": "number, oldest limit of search, in Myr before present -  must be used with age_top",
        "format": "string, Desired output format"
      },
      "examples": ["?interval_name=Permian", "?age=271", "?age_top=200&age_bottom=250"],
      "fields": {
        "geometry",
        "col_id",


      }
    }


  };

  defs["unit"] = {
    "description": "Gets all attributes of a given column",
    "options": {
      "parameters": {

      },
      "output_formats": "json",
      "examples": [],
      "fields": {

      }
    }
  };

  defs["units"] = {
    "description": "Gets all attributes of a given column",
    "options": {
      "parameters": {

      },
      "output_formats": "json",
      "examples": [],
      "fields": {

      }
    }
  };

  defs["fossils"] = {
    "description": "Gets all attributes of a given column",
    "options": {
      "parameters": {

      },
      "output_formats": "json",
      "examples": [],
      "fields": {

      }
    }
  };

  defs["stats"] = {
    "description": "Gets all attributes of a given column",
    "options": {
      "parameters": {

      },
      "output_formats": "json",
      "examples": [],
      "fields": {

      }
    }
  };

  def["lith_definitions"] = {
    "description": "Gets all attributes of a given column",
    "options": {
      "parameters": {

      },
      "output_formats": "json",
      "examples": [],
      "fields": {

      }
    }
  };

  def["lithatt_definitions"] = {
    "description": "Gets all attributes of a given column",
    "options": {
      "parameters": {

      },
      "output_formats": "json",
      "examples": [],
      "fields": {

      }
    }
  };

  def["environ_definitions"] = {
    "description": "Gets all attributes of a given column",
    "options": {
      "parameters": {

      },
      "output_formats": "json",
      "examples": [],
      "fields": {

      }
    }
  };

  def["interval_definitions"] = {
    "description": "Gets all attributes of a given column",
    "options": {
      "parameters": {

      },
      "output_formats": "json",
      "examples": [],
      "fields": {

      }
    }
  };

  def["strat_names"] = {
    "description": "Gets all attributes of a given column",
    "options": {
      "parameters": {

      },
      "output_formats": "json",
      "examples": [],
      "fields": {

      }
    }
  };

  def["section_stats"] = {
    "description": "Gets all attributes of a given column",
    "options": {
      "parameters": {

      },
      "output_formats": "json",
      "examples": [],
      "fields": {

      }
    }
  };

  def["paleogeography"] = {
    "description": "Gets all attributes of a given column",
    "options": {
      "parameters": {

      },
      "output_formats": "json",
      "examples": [],
      "fields": {

      }
    }
  };

  def["geologic_units"] = {
    "description": "Gets all attributes of a given column",
    "options": {
      "parameters": {

      },
      "output_formats": "json",
      "examples": [],
      "fields": {

      }
    }
  };

  def["geologic_units/map"] = {
    "description": "Gets all attributes of a given column",
    "options": {
      "parameters": {

      },
      "output_formats": "json",
      "examples": [],
      "fields": {

      }
    }
  };

  // This is the primary dictionary for all field definitions
  defs.define = {
    "id": "integer, unique identifier",
    "unit_id": "integer, unique identifier for unit",
    "section_id": "integer, unique identifier for section (package)",
    "col_id": "integer, unique identifier for column",
    "strat_name": "text, informal unit name",
    "Mbr": "text, lithostratigraphic member",
    "Fm": "text, lithostratigraphic formation",
    "Gp": "text, lithostratigraphic group",
    "SGp": "text, lithostratigraphic supergroup",
    "era": "string, containing international chronostratigraphic period",
    "period": "string, containing international chronostratigraphic period",
    "max_thick": "number, maximum thickness in meters",
    "min_thick": "number, minimum thickess in meters (NB some zero values may not have meaning)",
    "color": "text, recommended coloring for units baesd on dominant lithology",
    "FO_interval": "text, chronostratigraphic interval containing initiation/earliest(oldest) age",
    "FO_h": "integer, incates position within interval of initiation, 0=at base of interval",
    "FO_age": "number, age of FO_interval base in Myr before present",
    "b_age": "number, continuous time age model estimated for initiation, in Myr before present",
    "early_age": "number, oldest age, Myr before present",
    "LO_interval": "text, chronostratigraphic interval containing truncation/latest(youngest) age",
    "LO_h": "integer, incates position within interval of truncation, 0=at top of interval",
    "LO_age": "number, age of FO_interval top in Myr before present",
    "t_age": "number, continuous time age model estimated for truncation, in Myr before present",
    "late_age": "number, youngest age, Myr before present",
    "position_bottom": "number, estimated position of unit relative to other units in section",
    "lith": "text, specific lithology",
    "lith_type": "text, general lithology type",
    "lith_class": "text, general lithology class",
    "environ": "text, specific environment",
    "environ_type": "general environment type",
    "environ_class": "text, general lithology class",
    "pbdb": "number of matching Paleobiology Database fossil collections",
    "units": "integer, number of units",
    "notes": "text, notes releavnt to containing element",
    "project": "text, name of project",
    "geom": "geometry",
    "area": "area in square kilometers"
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
