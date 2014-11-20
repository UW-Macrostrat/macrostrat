(function() {
  var async = require("async");

  var defs = {};

  // Instead of adding metadata to each route in api.js, we are going to do it here
  defs["/column"] = {
    "description": "Get all units of a given column, optionally with geometry",
    "visible": true,
    "options": {
      "parameters": {
        "id": "integer, get a column by unique identifier",
        "lat": "number, decimal degree latitude, WGS84",
        "lng": "number, decimal degree longitude, WGS84",
        "geom": "boolean, whether associated geometry is returned",
        "response": "Can be 'short' or 'long'"
      },
      "output_formats": ["json"],
      "examples": [
        "/api/columns?id=17",
        "/api/columns?lat=50&lng=-80"
      ],
      "fields":[ 
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
        "geom",
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
  };
  
  defs["/columns"] = {
    "description": "Get all colums containing one or more units matching specfied search criteria",
    "visible": true,
    "options": {
      "parameters": {
        "interval_name": "text, name of search time interval",
        "age": "number, search age in Myr before present",
        "age_top": "number, youngest limit of search, in Myr before present - must be used with age_bottom",
        "age_bottom": "number, oldest limit of search, in Myr before present -  must be used with age_top",
        "lith": "string, return only columns with units containing specified lithology, lith defined in /lith_definitions",
        "lith_class": "string, return only columsn with units containing specified lithology, lith_class defined in /lith_definitions",
        "lith_type": "string, return only columsn with units containing specified lithology, lith_type defined in /lith_definitions",
        "all": "Show all results",
        "format": "string, Desired output format"
      },
      "output_formats": ["json", "csv", "geojson", "geojson_bare", "topojson", "topojson_bare"],
      "examples": [
        "/api/columns?interval_name=Permian",
        "/api/columns?age=271",
        "/api/columns?age_top=200&age_bottom=250"
      ],
      "fields": [
        "col_id": "unique identifier for column",
        "area": "area of column in square kilometers",
        "units": "number of units in column",
        "unit_id": "unique identifier of units in column",
        "max_thick": "sum of maximum unit thickness (m) in column",
        "min_thick": "sum of minimum unit thickness (m) in column",
        "lith_max_thick": "sum of maximum unit thickness (m) in column for specified lithology",
        "lith_min_thick": "sum of minimum unit thickness (m) in column for specified lithology",
        "lith_types": "summary of lithology types present in column"
      ]
    }
  };

  defs["/sections"] = {
    "description": "Get all sections for a given column",
    "visible": true,
    "options": {
      "parameters": {
        "col_id": "integer, column ID",
        "all": "Return all sections",
        "format": "string, Desired output format"
      },
      "output_formats": ["json", "csv"],
      "examples": [
        "/api/sections?all",
        "/api/sections?col_id=49"
      ],
      "fields": [
        "id",
        "col_id",
        "bottom",
        "top",
        "units",
        "fossils"
      ]
    }
  };

  defs["/unit"] = {
    "description": "Gets all data for a given unit",
    "visible": true,
    "options": {
      "parameters": {
        "id": "Unit id",
        "pbdb": "Boolean",
        "response": "Can be 'short' or 'long'"
      },
      "output_formats": ["json"],
      "examples": [
        "api/unit?id=527",
        "api/unit?id=527&pbdb=true"
      ],
      "fields": [
        "id",
        "section_id",
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
        "lith_class",
        "lith_type",
        "lith",
        "environ_class",
        "environ_type",
        "environ",
        "pbdb",
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
  };

  defs["/units"] = {
    "description": "Return all units given an age or time range",
    "visible": true,
    "options": {
      "parameters": {
        "interval_name": "The name of a time interval",
        "age": "A valid age",
        "age_top": "A valid age - must be used with age_bottom and be less than age_bottom",
        "age_bottom": "A valid age - must be used with age_top and be greater than age_top",
        "section_id": "Integer, a valid section id",
        "col_id": "Integer, a valid column id",
        "response": "Can be 'short' or 'long' - default is 'short'"
      },
      "output_formats": ["json", "csv"],
      "examples": [
        "api/units?interval_name=Permian",
        "api/units?age=271",
        "api/units?interval_name=Permian&response=long",
        "api/units?section_id=107&col_id=22&format=csv"
      ],
      "fields": [
        "id",
        "section_id",
        "col_id",
        "col_area",
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
        "lith_class",
        "lith_type",
        "lith",
        "environ_class",
        "environ_type",
        "environ",
        "pbdb",
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
  };

  defs["/fossils"] = {
    "description": "Returns all fossils given an interval name or age range",
    "visible": true,
    "options": {
      "parameters": {
        "interval_name": "The name of a time interval",
        "age": "A valid age",
        "age_top": "A valid age - must be used with age_bottom and be less than age_bottom",
        "age_bottom": "A valid age - must be used with age_top and be greater than age_top",
        "format": "Desired output format"
      },
      "output_formats": ["geojson", "geojson_bare", "topojson", "topojson_bare"],
      "examples": [
        "/api/fossils?interval_name=Permian",
        "/api/fossils?age=271",
        "/api/fossils?age_top=200&age_bottom=250"
      ],
      "fields": [
        "collection_no",
        "occ",
        "unit_id"
      ]
    }
  };

  defs["/stats"] = {
    "description": "Returns statistics about the macrostrat database",
    "visible": true,
    "options": {
      "parameters": {
        "all": "Show all results",
        "format": "Desired output format"
      },
      "output_formats": ["json", "csv"],
      "examples": ["api/stats?all"],
      "fields": [
        "project",
        "packages",
        "units",
        "pbdb_collections"
      ]
    }
  };

  defs["/lith_definitions"] = {
    "description": "Returns all lith definitions",
    "visible": true,
    "options": {
      "parameters": {
        "id": "Lith id",
        "lith_class": "lith class",
        "lith_type": "lith_type",
        "all": "return all lith definitions"
      },
      "output_formats": ["json", "csv"],
      "examples": [
        "api/lith_definitions?id=3",
        "api/lith_definitions?all",
        "api/lith_definitions?lith_class=sedimentary"
      ],
      "fields": [
        "id",
        "lith",
        "lith_type",
        "lith_class",
        "lith_color"
      ]
    }
  };

  defs["/lithatt_definitions"] = {
    "description": "Returns lithatt definition",
    "visible": true,
    "options": {
      "parameters": {
        "att_type": "lithatt type",
        "lith_att": "lith_att",
        "id": "a lith att id",
        "all": "return all lith_att definitions",
        "format": "Desired output format"
      },
      "output_formats": ["json", "csv"],
      "examples": [
        "api/lithatt_definitions?all",
        "api/lithatt_definitions?lith_type=bedform"
      ],
      "fields": [
        "id",
        "lith_att",
        "att_type"
      ]
    }
  };

  defs["/environ_definitions"] = {
    "description": "Returns environment definitions",
    "visible": true,
    "options": {
      "parameters": {
        "environ_class": "environment class",
        "environ_type": "environment type",
        "environ": "environment",
        "id": "an environment id",
        "all": "return all environment definitions",
        "format": "Desired output format"
      },
      "output_formats": ["json", "csv"],
      "examples": [
        "api/environ_definitions?all",
        "api/environ_definitions?environ=sand%20shoal"
      ],
      "fields": [
        "id",
        "environ",
        "environ_type",
        "environ_class"
      ]
    }
  };

  defs["/interval_definitions"] = {
    "description": "Returns interval definitions",
    "visible": true,
    "options": {
      "parameters": {
        "timescale": "timescale to use",
        "id": "an interval id",
        "all": "return all interval definitions",
        "format": "Desired output format"
      },
      "output_formats": ["json", "csv"],
      "examples": [
        "api/interval_definitions?all",
        "api/interval_definitions?id=366",
        "api/interval_definitions?timescale=new%20zealand%20ages"
      ],
      "fields": [
        "id",
        "interval_name",
        "late_age",
        "early_age"
      ]
    }
  };

  defs["/strat_names"] = {
    "description": "Returns strat names",
    "visible": true,
    "options": {
      "parameters": {
        "id": "strat id",
        "name": "strat name",
        "rank": "strat rank",
        "all": "return all strat names",
        "format": "Desired output format"
      },
      "output_formats": ["json", "csv"],
      "examples": [
        "api/strat_names?all",
        "api/strat_names?rank=Fm"
      ],
      "fields": [
        "name",
        "rank",
        "id",
        "bed",
        "bed_id",
        "mbr",
        "mbr_id",
        "fm",
        "fm_id",
        "gp",
        "gp_id",
        "sgp",
        "sgp_id",
        "early_age",
        "late_age"
      ]
    }
  };

  defs["/section_stats"] = {
    "description": "Return section stats",
    "visible": true,
    "options": {
      "parameters": {
        "all": "return all section stats",
        "format": "Desired output format"
      },
      "output_formats": ["json", "csv"],
      "examples": [
        "api/section_stats?all",
        "api/section_stats?all&format=csv"
      ],
      "fields": [
        "project",
        "col_id",
        "section_id",
        "units",
        "max_thick",
        "min_thick",
        "t_age",
        "b_age"
      ]
    }
  };

  defs["/paleogeography"] = {
    "description": "Returns paleogeography geometry",
    "visible": true,
    "options": {
      "parameters": {
        "age": "Can be between 0 and 550",
        "interval_name": "A named time interval",
        "format": "Desired output format"
      },
      "output_formats": ["geojson", "geojson_bare", "topojson", "topojson_bare"],
      "examples": [
        "api/paleogeography?interval_name=Permian",
        "api/paleogeography?age=271&format=topojson"
      ],
      "fields": [
        "plateid"
      ]
    }
  };

  defs["/geologic_units"] = {
    "description": "What's at a point",
    "visible": true,
    "options": {
      "parameters": {
        "lat": "A valid latitude",
        "longitude": "A valid longitude",
        "type": "Return only from given sources - can be 'gmna', 'gmus', 'column', or any combination thereof",
        "response": "can be 'short' or 'long'",
        "geo": "Whether geometry of features should also be returned",
        "format": "Desired output format"
      },
      "output_formats": ["json"],
      "examples": [
        "/api/geologic_units?lat=43&lng=-89.3",
        "/api/geologic_units?lat=43&lng=-89&geo=true",
        "/api/geologic_units?lat=43&lng=-89&type=gmus"
      ],
      "fields": [
        "id",
        "col_name",
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
      ]
    }
  };

  defs["/geologic_units/intersection"] = {
    "description": "What's under a line",
    "visible": true,
    "options": {
      "parameters": {
        "line": "A valid linestring in WKT format",
        "type": "Return only from given sources - can be 'gmna' or 'gmus'"
      },
      "output_formats": ["json"],
      "examples": [
        "/api/geologic_units/intersection?line=LINESTRING(-91.8896484375 43.26120612479979,-83.1005859375 43.068887774169625)",
        "/api/geologic_units/intersection?line=LINESTRING(-91.8896484375 43.26120612479979,-83.1005859375 43.068887774169625)&type=gmus"
      ],
      "fields": [
        "id",
        "unit_abbre",
        "rocktype",
        "lithology",
        "min_age",
        "max_age",
        "state", 
        "rocktype1", 
        "rocktype2",
        "rocktype3", 
        "unit_name", 
        "unit_age", 
        "unitdesc", 
        "strat_unit", 
        "unit_com"
      ]
    }
  };

  defs["/geologic_units/map"] = {
    "description": "Fetch polygons for mapping",
    "visible": true,
    "options": {
      "parameters": {
        "type": "type of geometry to use - can be 'gmus' (Geologic Map United States) or 'gmna' (Geologic Map North America)",
        "interval_name": "name of time interval to use",
        "format": "Desired output format"
      },
      "output_formats": ["geojson", "topojson"],
      "examples": [
        "api/geologic_units/map?type=gmus&interval_name=Permian",
        "api/geologic_units/map?type=gmna&interval_name=Jurassic&format=topojson"
      ],
      "fields": [
        "gid",
        "unit_age",
        "rocktype1",
        "rocktype2",
        "cmin_age"
      ]
    }
  };

  defs["/mobile/point"] = {
    "description": "Get GMUS unit and Macrostrat polygon for a given point",
    "visible": true,
    "options": {
      "parameters": {
        "lat": "A valid latitude",
        "lng": "A valid longitude",
        "geo_format": "Output geometry format - can be 'wkt' or 'geojson'; Defaults to 'geojson'"
      },
      "output_formats": ["json"],
      "examples": [
        "api/mobile/point?lat=43&lng=-89",
        "api/mobile/point?lat=43&lng=-89&geo_format=wkt"
      ],
      "fields": [
        "gid",
        "unit_name",
        "col_id",
        "col_poly"
      ]
    }
  };

  defs["/mobile/point_details"] = {
    "description": "Get GMUS unit description and Macrostrat units for a given location. A valid latitude and longitude or column ID and GMUS unit ID are required.",
    "visible": true,
    "options": {
      "parameters": {
        "lat": "A valid latitude",
        "lng": "A valid longitude",
        "col_id": "A valid column ID",
        "unit_id": "A valid GMUS unit ID",
        "geo_format": "Output geometry format - can be 'wkt' or 'geojson'; Defaults to 'geojson'"
      },
      "output_formats": ["json"],
      "examples": [
        "api/mobile/point_details?lat=43&lng=-89",
        "api/mobile/point_details?col_id=187&unit_id=184506&geo_format=wkt"
      ],
      "fields": [
        "gid",
        "unit_name",
        "col_id",
        "col_poly"
      ]
    }
  };

  defs["/mobile/fossil_collections"] = {
    "description": "Get Paleobiology Database fossil collection numbers for a given Macrostrat unit",
    "visible": true,
    "options": {
      "parameters": {
        "unit_id": "Macrostrat unit ID"
      },
      "output_formats": ["json"],
      "examples": [
        "/mobile/fossil_collections?unit_id=6132"
      ],
      "fields": [
        "pbdb_collections"
      ]
    }
  };

  defs["/editing/map"] = {
    "visible": false
  };

  defs["/editing/map/update"] = {
    "visible": false
  };

  defs["/editing/units"] = {
    "visible": false
  };

  defs["/editing/units/update"] = {
    "visible": false
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
    "area": "area in square kilometers",
    "plateid": "integer, unique GPlates ID"
  };

  module.exports = defs;
}());
