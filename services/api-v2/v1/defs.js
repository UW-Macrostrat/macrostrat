(function() {
  var async = require("async");

  var defs = {};

  // Instead of adding metadata to each route in api.js, we are going to do it here
  defs["/column"] = {
    "description": "*** Deprecated. Will not exist in v2. Please use /column or /units instead.*** Get all units of a given column",
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
        "/api/column?id=17",
        "/api/column?lat=50&lng=-80"
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
        "lith": "string, return only columns with units containing specified lithology, lith defined in /defs/lithologies",
        "lith_class": "string, return only columns with units containing specified lithology, lith_class defined in /defs/lithologies",
        "lith_type": "string, return only columns with units containing specified lithology, lith_type defined in /defs/lithologies",
        "strat_name": "string, return only columns that contain a given unit name",
        "strat_id": "number, one or more comma-separated strat_ids, as definied in /defs/strat_names",
        "col_id": "number, one or more comma-separated column IDs",
        "all": "Show all results",
        "lat": "number, decimal degree latitude, WGS84",
        "lng": "number, decimal degree longitude, WGS84",
        "adjacents": "boolean, if lat/lng or col_id is specified, optionally return all columns that touch the polygon containing the supplied lat/lng",
        "response": "Can be 'short' or 'long' - default is 'short'",
        "format": "string, desired output format"
      },
      "output_formats": ["json", "csv", "geojson", "geojson_bare", "topojson", "topojson_bare"],
      "examples": [
        "/api/columns?interval_name=Permian",
        "/api/columns?age=271",
        "/api/columns?age_top=200&age_bottom=250",
        "/api/columns?strat_name=mancos&format=geojson_bare",
        "/api/columns?lat=43&lng=-89&adjacents=true"
      ],
      "fields": [
        "col_id",
        "col_group",
        "area",
        "units",
        "unit_id",
        "max_thick",
        "min_thick",
        "lith_max_thick",
        "lith_min_thick",
        "lith_type",
        "col_name",
        "col_group",
        "col_group_id",
        "b_age",
        "t_age",
        "sections",
        "pbdb_collections",
        "pbdb_occs"
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
        "top",
        "top_age",
        "bottom",
        "bottom_age",
        "units",
        "fossils"
      ]
    }
  };

  defs["/units"] = {
    "description": "all Macrostrat units matching search criteria",
    "visible": true,
    "options": {
      "parameters": {
        "id": "integer, a valid unit id",
        "section_id": "integer, a valid section id",
        "col_id": "integer, a valid column id",
        "interval_name": "chronostratigraphic time interval name",
        "age": "numerical age in millions of years before present",
        "age_top": "numerical age (Ma) - must be used with age_bottom and be less than age_bottom",
        "age_bottom": "numerical age (Ma) - must be used with age_top and be greater than age_top",
        "lith": "specific lithology (e.g., shale, sandstone)",
        "lith_type": "groups of lithologies (e.g., carbonate, siliciclastic)",
        "lith_class": "general lithologies (sedimentary, igneous, metamorphic)",
        "environ": "specific environment",
        "environ_type": "groups of environments",
        "environ_class": "general environments",
        "strat_name": "a fuzzy stratigraphic name to match units to",
        "strat_id": "a single or comma-separated list of stratigraphic ids (can be retrieved from /defs/strat_names",
        "response": "Can be 'short' or 'long' - default is 'short'"
      },
      "output_formats": ["json", "csv"],
      "examples": [
        "api/units?interval_name=Permian",
        "api/units?age=271",
        "api/units?interval_name=Permian&response=long",
        "api/units?strat_id=1205,4260",
        "api/units?strat_name=mancos",
        "api/units?section_id=107&col_id=22&format=csv"
      ],
      "fields": [
        "id",
        "section_id",
        "project_id",
        "col_id",
        "col_area",
        "strat_name",
        "strat_name_id",
        "Mbr",
        "Fm",
        "Gp",
        "SGp",
        "era",
        "period",
        "max_thick",
        "min_thick",
        "u_color",
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
        "notes",
        "color",
        "text_color"
      ]
    }
  };

  defs["/unit_contacts"] = {
    "description": "unit contact relationships",
    "visible": true,
    "options": {
      "parameters": {
        "all": "return all contacts",
        "section_id": "number, return contacts only for specified section_id"
      },
      "output_formats": ["json","csv"],
      "examples": [
        "/api/unit_contacts?all",
        "api/unit_contacts?section_id=22"
      ],
      "fields": [
        "unit_id",
        "contact",
        "with_unit"
      ]
    }


  }

  defs["/fossils"] = {
    "description": "Paleobiology Database (http://paleobiodb.org) collections matched to Macrostrat units",
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

  defs["/pbdb_report"] = {
    "description": "Get distinct strat_names that have or have not been matched to one or more Paleobiology Database (http://paleobiodb.org) collections",
    "visible": true,
    "options": {
      "parameters": {
        "matched": "show only matched Macrostrat units, default is to show unmatched strat_names",
        "project_id": "integer, limit results to project",
        "showpairs": "show all PBDB and Macrostrat key pairs",
        "showorphans": "show all PBDB authorities with no opinion data of any kind",
        "format": "Desired output format"
      },
      "output_formats": ["json", "csv"],
      "examples": [
        "/api/pbdb_report?project_id=1&matched"
      ],
      "fields": [
        "collections",
        "strat_name",
        "strat_name_id"
      ]
    }
  };


  defs["/stats"] = {
    "description": "statistics about the Macrostrat database",
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

  defs["/defs"] = {
    "description": "Routes giving access to standard fields and dictionaries used in Macrostrat",
    "visible": true
  };

  defs["/defs/lithologies"] = {
    "description": "Returns all lithology definitions",
    "parent": "definitions",
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
        "api/defs/lithologies?id=3",
        "api/defs/lithologies?all",
        "api/defs/lithologies?lith_class=sedimentary"
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

  defs["/defs/lithology_attributes"] = {
    "description": "Returns lithology attribute definitions",
    "parent": "definitions",
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
        "api/defs/lithology_attributes?all",
        "api/defs/lithology_attributes?lith_type=bedform"
      ],
      "fields": [
        "id",
        "lith_att",
        "att_type"
      ]
    }
  };

  defs["/defs/environments"] = {
    "description": "Returns environment definitions",
    "parent": "definitions",
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
        "api/defs/environments?all",
        "api/defs/environments?environ=sand%20shoal"
      ],
      "fields": [
        "id",
        "environ",
        "environ_type",
        "environ_class"
      ]
    }
  };

  defs["/defs/intervals"] = {
    "description": "Returns all time interval definitions",
    "parent": "definitions",
    "visible": true,
    "options": {
      "parameters": {
        "timescale": "timescale to use",
        "id": "an interval id",
        "all": "return all interval definitions",
        "late_age": "a late age",
        "early_age": "an early age",
        "age": "integer, an age - will find all intervals that overlap with this age",
        "format": "Desired output format"
      },
      "output_formats": ["json", "csv"],
      "examples": [
        "api/defs/intervals?all",
        "api/defs/intervals?id=366",
        "api/defs/intervals?timescale=new%20zealand%20ages",
        "api/defs/intervals?late_age=0&early_age=130",
        "api/defs/interals?timescale=international&age=100"
      ],
      "fields": [
        "id",
        "name",
        "abbrev",
        "late_age",
        "early_age",
        "type",
        "color"
      ]
    }
  };

  defs["/defs/strat_names"] = {
    "description": "Returns strat names",
    "parent": "definitions",
    "visible": true,
    "options": {
      "parameters": {
        "id": "unique id",
        "name": "lithostratigraphic name, exact match",
        "name_like": "lithostratigraphic name, with open-ended string matching",
        "rank": "lithostratigraphic rank",
        "all": "return all lithostratigraphic names",
        "format": "Desired output format"
      },
      "output_formats": ["json", "csv"],
      "examples": [
        "api/defs/strat_names?all",
        "api/defs/strat_names?rank=Fm"
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
        "late_age",
        "gsc_lexicon"
      ]
    }
  };

  defs["/defs/timescales"] = {
    "description": "Returns timescales used by Macrostrat",
    "parent": "definitions",
    "visible": true,
    "options": {
      "parameters": {
        "all": "return all available timescales",
        "format": "Desired output format"
      },
      "output_formats": ["json", "csv"],
      "examples": [
        "api/defs/timescales?all"
      ],
      "fields": [
        "id",
        "timescale"
      ]
    }
  };

  defs["/defs/projects"] = {
    "description": "Returns available Macrostrat projects",
    "parent": "definitions",
    "visible": true,
    "options": {
      "parameters": {
        "all": "return all available projects",
        "format": "Desired output format"
      },
      "output_formats": ["json", "csv"],
      "examples": [
        "api/defs/timescales?all"
      ],
      "fields": [
        "id",
        "project",
        "timescale_id"
      ]
    }
  };

  defs["/defs/measurements"] = {
    "description": "Returns all measurements definitions",
    "parent": "definitions",
    "visible": true,
    "options": {
      "parameters": {
        "id": "measurement id",
        "measurement_class": "measurement_class",
        "measurement_type": "measurement_type",
        "all": "return all measurement definitions"
      },
      "output_formats": ["json", "csv"],
      "examples": [
        "api/defs/measurements?id=3",
        "api/defs/measurements?all",
        "api/defs/measurements?measurement_class=geochemical"
      ],
      "fields": [
        "id",
        "measurement",
        "measurement_type",
        "measurement_class"
      ]
    }
  };

  defs["/defs/groups"] = {
    "description": "Returns all column groups",
    "parent": "definitions",
    "visible": true,
    "options": {
      "parameters": {
        "all": "return all column groups"
      },
      "output_formats": ["json", "csv"],
      "examples": [
        "api/defs/groups?all",
      ],
      "fields": [
        "col_group_id",
        "col_group"
      ]
    }
  };

  defs["/section_stats"] = {
    "description": "Return section stats for Macrostrat",
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
    "description": "Returns paleogeography geometry from http://www.gplates.org, courtesy of Mark Turner and Mike Gurnis. Note that for complete and recent reconstructions, original GPlates data services should be used - http://gplates.gps.caltech.edu:8080. If you use this service and provide attribution, you should cite GPlates via this service.",
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
    "description": "Geologic map units. State-level (gmus) data adapated from http://mrdata.usgs.gov/geology/state/, Continental-scale North American data (gmna) adapted from the 2005 Geologic Map of North America (http://ngmdb.usgs.gov/gmna/)",
    "visible": true,
    "options": {
      "parameters": {
        "lat": "A valid latitude",
        "lng": "A valid longitude",
        "type": "(Required) Return only from given sources - can be 'gmna', 'gmus', or both",
        "unit_name": "string, a stratigraphic name to search for (GMUS only)",
        "unit_link": "string, a GMUS unit_link. If format=json, will return one record with unique attributes, if a geographic output format is request it will return all polygons with the given unit_link (GMUS only)",
        "gid": "integer, a polygon GID to search for",
        "format": "Desired output format"
      },
      "output_formats": ["json", "geojson", "geojson_bare", "topojson", "topojson_bare"],
      "examples": [
        "/api/geologic_units?lat=43&lng=-89.3&type=gmus",
        "/api/geologic_units?lat=43&lng=-89&format=geojson_bare",
        "/api/geologic_units?lat=43&lng=-89&type=gmna"
      ],
      "fields": [
        "gid",
        "interval_color",
        "lith1",
        "lith2",
        "lith3",
        "lith4",
        "lith5",
        "macro_units",
        "min_age",
        "max_age",
        "rt1",
        "rt2",
        "rt3",
        "unit_age",
        "unit_com",
        "unit_link",
        "unit_name",
        "unitdesc",
        "strat_unit",
        "unit_abrre",
        "rocktype",
        "lithology",
        "interval_name"
      ]
    }
  };

  defs["/geologic_units/intersection"] = {
    "description": "Geologic units under a WKT shape. State-level geologic map (gmus) data adapted from http://mrdata.usgs.gov/geology/state/, continent-scale (gmna) data adapted from http://ngmdb.usgs.gov/gmna/",
    "visible": true,
    "options": {
      "parameters": {
        "shape": "(Required) A valid WKT shape",
        "line": "(Deprecated) alias for shape",
        "type": "(Required) Return only from given sources - can be 'gmna' or 'gmus'",
        "buffer": "(Optional) Buffer the linestring by a given number of kilometers (default is 35)"
      },
      "output_formats": ["json", "geojson", "topojson", "geojson_bare", "topojson_bare"],
      "examples": [
        "/api/geologic_units/intersection?line=LINESTRING(-92 43,-83 43)&format=geojson_bare&type=gmus",
        "/api/geologic_units/intersection?line=LINESTRING(-92 43,-83 43)&type=gmus",
        "/api/geologic_units/intersection?line=LINESTRING(-92 43,-83 43)&type=gmna&format=geojson_bare&buffer=50",
        "/api/geologic_units/intersection?shape=POLYGON((-89.7 42.9,-89.7 43.2,-88.9 43.2,-88.9 42.9,-89.7 42.9))&type=gmus&buffer=0&format=geojson_bare"
      ],
      "fields": [
        "id",
        "unit_abbre",
        "rocktype",
        "lith",
        "min_age",
        "max_age",
        "color"
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

  defs["/mobile"] = {
    "description": "Simplified data delivery, ideal for mobile applications",
    "visible": true
  };


  defs["/mobile/point"] = {
    "description": "Get state-level map (gmus) unit and Macrostrat polygon for a given point",
    "parent": "mobile",
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
    "description": "Get state-level geologic map (gmus) unit description and Macrostrat units for a given location. A valid latitude and longitude or column ID and GMUS unit ID are required.",
    "parent": "mobile",
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
    "description": "Get Paleobiology Database (http://paleobiodb.org) fossil collection numbers matched to a given Macrostrat unit",
    "parent": "mobile",
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
    "col_group": "text, the group the column belongs to",
    "unit_id": "integer, unique identifier for unit",
    "section_id": "integer, unique identifier for section (package)",
    "col_id": "integer, unique identifier for column",
    "col_name": "text, name of column",
    "col_group_id": "integer, ID of column group",
    "sections": "int[], sections that belong to the column",
    "pbdb_collections": "integer, count of PBDB collections in units in column",
    "pbdb_occs": "integer, count of PBDB occurrences in units in column",
    "project_id": "unique identifier for project, corresponds to general geographic region",
    "strat_name": "text, informal unit name",
    "strat_name_id": "integer, unique identifier for known stratigraphic name (see /defs/strat_names)",
    "name": "interval name",
    "Mbr": "text, lithostratigraphic member",
    "Fm": "text, lithostratigraphic formation",
    "Gp": "text, lithostratigraphic group",
    "SGp": "text, lithostratigraphic supergroup",
    "era": "string, containing international chronostratigraphic period",
    "period": "string, containing international chronostratigraphic period",
    "max_thick": "number, maximum thickness in meters",
    "min_thick": "number, minimum thickess in meters (NB some zero values may be equivalent to NULL, not zero)",
    "color": "text, recommended coloring for units based on dominant lithology",
    "u_color": "text, original color for unit",
    "text_color": "text, recommended coloring for text based on color",
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
    "measurement": "text, specific measurement",
    "measurement_type": "text, general measurement type",
    "measurement_class": "text, general measurement class",
    "lith_max_thick": "number, thickness of specified lithology, based on proportion of unit(s)",
    "lith_min_thick": "number, thickness of specified lithology, based on proportion of unit(s)",
    "environ": "text, specific environment",
    "environ_type": "general environment type",
    "environ_class": "text, general lithology class",
    "pbdb": "number of matching Paleobiology Database fossil collections",
    "units": "integer, number of units",
    "notes": "text, notes releavnt to containing element",
    "project": "text, name of project",
    "geom": "geometry",
    "area": "area in square kilometers",
    "plateid": "integer, unique GPlates ID",
    "with_unit": "unit in contact with unit_id",
    "contact": "relative position of units, read for unit_id,  'contact' = with_unit",
    "unit_abbre": "text, unit abbreviation",
    "rocktype": "text, unit rock type",
    "min_age": "text, the minimum age of the unit, using the International time scale",
    "max_age": "text, the maximum age of the unit, using the International time scale",
    "timescale": "text, name of timescale",
    "project": "text, name of project",
    "timescale_id": "integer, unique identifier for timescale used in project",
    "top": "text, named time interval that contains the top of the section",
    "top_age": "number, minimum age of the section in millions of years",
    "bottom": "text, named time interval that contains the bottom of the section",
    "bottom_age": "number, maximum age of the section in millions of years",
    "abbrev": "standard abbreviation for interval name",
    "gsc_lexicon": "Canada Geological Survey Lexicon web id; data for some names can be accessed via link: http://weblex.nrcan.gc.ca/html/000000/GSCC00053000747.html",
    "col_group_id": "integer, unique identifier for column group",
    "col_group": "text, name of column group"
  };

  module.exports = defs;
}());
