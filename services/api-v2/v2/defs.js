(function() { 
  var defs = {
  "/columns": {
    "description": "Get all colums containing one or more units matching specfied search criteria",
    "visible": true,
    "options": {
      "parameters": {
        "col_id": "integer, one or more comma-separated column IDs",
        "unit_id": "integer, one or more comma-separated unit IDs",
        "section_id": "integer, one or more comma-separated section IDs",
        "interval_name": "string, name of a valid time interval from /defs/intervals",
        "age": "number, search age in Myr before present",
        "age_top": "number, youngest limit of search, in Myr before present - must be used with age_bottom",
        "age_bottom": "number, oldest limit of search, in Myr before present -  must be used with age_top",
        "lith": "string, return only columns with units containing specified lithology, lith defined in /defs/lithologies",
        "lith_class": "string, return only columns with units containing specified lithology, lith_class defined in /defs/lithologies",
        "lith_type": "string, return only columns with units containing specified lithology, lith_type defined in /defs/lithologies",
        "strat_name": "string, return only columns that contain a given unit name",
        "strat_name_id": "number, one or more comma-separated strat_ids, as defined in /defs/strat_names",
        "all": "Show all columns",
        "lat": "number, decimal degree latitude, WGS84",
        "lng": "number, decimal degree longitude, WGS84",
        "adjacents": "boolean, if lat/lng or col_id is specified, optionally return all columns that touch the polygon containing the supplied lat/lng",
        "project_id": "integer, one or more comma-separated project IDs as defined in /defs/projects",
        "response": "Any available response_type. Default is short.",
        "format": "string, desired output format"
      },
      "response_types": [
        "short",
        "long"
      ],
      "output_formats": [
        "json",
        "csv",
        "geojson",
        "geojson_bare",
        "topojson",
        "topojson_bare"
      ],
      "examples": [
        "/api/columns?interval_name=Permian",
        "/api/columns?age=271",
        "/api/columns?age_top=200&age_bottom=250",
        "/api/columns?strat_name=mancos&format=geojson_bare",
        "/api/columns?lat=43&lng=-89&adjacents=true"
      ],
      "fields": [
        "col_id",
        "col_name",
        "col_group",
        "col_group_id",
        "group_col_id",
        "col_area",
        "project_id",
        "max_thick",
        "min_thick",
        "b_age",
        "t_age",
        "pbdb_collections",
        "environ_class",
        "environ_type",
        "environ",
        "lith",
        "lith_type",
        "lith_class"
      ]
    }
  },
  "/sections": {
    "description": "Get all sections for a given column",
    "visible": true,
    "options": {
      "parameters": {
        "col_id": "integer, one or more comma-separated column IDs",
        "all": "Return all sections",
        "format": "string, Desired output format"
      },
      "output_formats": [
        "json",
        "csv"
      ],
      "examples": [
        "/api/sections?all",
        "/api/sections?col_id=49"
      ],
      "fields": [
        "section_id",
        "col_id",
        "t_interval",
        "t_age",
        "b_interval",
        "b_age",
        "units",
        "pbdb_collections"
      ]
    }
  },
  "/units": {
    "description": "all Macrostrat units matching search criteria",
    "visible": true,
    "options": {
      "parameters": {
        "unit_id": "integer, a valid unit id",
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
        "strat_name_id": "a single or comma-separated list of stratigraphic ids (can be retrieved from /defs/strat_names",
        "lat": "number, decimal degree latitude, WGS84",
        "lng": "number, decimal degree longitude, WGS84",
        "adjacents": "boolean, if lat/lng or col_id is specified, optionally return all units in columns that touch the polygon containing the supplied lat/lng",
        "project_id": "a Macrostrat project ID",
        "response": "Any available response_type. Default is short.",
        "format": "string, desired output format",
        "geom_age": "If requesting a geographic format, specifies which age to use for the primary coordinates. Accepted parameters are 'modern' (clat, clng), 'top' (t_plat, t_plng) and 'bottom' (b_plat, b_plng). Default is 'modern'"
      },
      "response_types": [
        "short",
        "long"
      ],
      "output_formats": [
        "json",
        "csv",
        "geojson",
        "topojson",
        "geojson_bare",
        "topojson_bare"
      ],
      "examples": [
        "api/units?interval_name=Permian",
        "api/units?age=271",
        "api/units?interval_name=Permian&response=long",
        "api/units?strat_id=1205,4260",
        "api/units?strat_name=mancos",
        "api/units?section_id=107&col_id=22&format=csv",
        "api/units?strat_id=1205&format=geojson_bare&geom_age=bottom"
      ],
      "fields": [
        "unit_id",
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
        "lith_class",
        "lith_type",
        "lith",
        "environ_class",
        "environ_type",
        "environ",
        "outcrop",
        "pbdb_collections",
        "notes",
        "color",
        "text_color",
        "t_int_id",
        "t_int_name",
        "t_int_age",
        "t_age",
        "t_prop",
        "units_above",
        "b_int_id",
        "b_int_name",
        "b_int_age",
        "b_age",
        "b_prop",
        "units_below",
        "clat",
        "clng",
        "t_plat",
        "t_plng",
        "b_plat",
        "b_plng"
      ]
    }
  },
  "/fossils": {
    "description": "Paleobiology Database (http://paleobiodb.org) collections matched to Macrostrat units",
    "visible": true,
    "options": {
      "parameters": {
        "interval_name": "The name of a time interval",
        "age": "A valid age",
        "age_top": "A valid age - must be used with age_bottom and be less than age_bottom",
        "age_bottom": "A valid age - must be used with age_top and be greater than age_top",
        "unit_id": "One or more comma-separated valid unit IDs",
        "col_id": "One or more comma-separated valid column IDs",
        "format": "Desired output format"
      },
      "output_formats": [
        "geojson",
        "geojson_bare",
        "topojson",
        "topojson_bare"
      ],
      "examples": [
        "/api/fossils?interval_name=Permian",
        "/api/fossils?age=271",
        "/api/fossils?age_top=200&age_bottom=250",
        "/api/fossils?col_id=446"
      ],
      "fields": [
        "cltn_id",
        "cltn_name",
        "pbdb_occs",
        "unit_id"
      ]
    }
  },
  "/pbdb_report": {
    "description": "Get distinct strat_names that have or have not been matched to one or more Paleobiology Database (http://paleobiodb.org) collections",
    "visible": true,
    "options": {
      "parameters": {
        "matched": "show only matched Macrostrat units, default is to show unmatched strat_names",
        "project_id": "integer, limit results to project",
        "showpairs": "show all PBDB and Macrostrat key pairs",
        "showorphans": "show all PBDB authorities with no opinion data of any kind",
        "showtime": "show all PBDB time interval definitions",
        "format": "Desired output format"
      },
      "output_formats": [
        "json",
        "csv"
      ],
      "examples": [
        "/api/pbdb_report?project_id=1&matched"
      ],
      "fields": [
        "collections",
        "strat_name",
        "strat_name_id"
      ]
    }
  },
  "/stats": {
    "description": "statistics about the Macrostrat database",
    "visible": true,
    "options": {
      "parameters": {
        "all": "Show all results",
        "format": "Desired output format"
      },
      "output_formats": [
        "json",
        "csv"
      ],
      "examples": [
        "api/stats?all"
      ],
      "fields": [
        "project_id",
        "project",
        "status",
        "columns",
        "packages",
        "units",
        "pbdb_collections"
      ]
    }
  },
  "/defs": {
    "description": "Routes giving access to standard fields and dictionaries used in Macrostrat",
    "visible": true
  },
  "/defs/lithologies": {
    "description": "Returns all lithology definitions",
    "parent": "definitions",
    "visible": true,
    "options": {
      "parameters": {
        "lith_id": "integer, one or more lithology ids",
        "lith_class": "string, lithology class",
        "lith_type": "string, lithology type",
        "all": "return all lithology definitions"
      },
      "output_formats": [
        "json",
        "csv"
      ],
      "examples": [
        "api/v2/defs/lithologies?lith_id=3",
        "api/v2/defs/lithologies?all",
        "api/v2/defs/lithologies?lith_class=sedimentary"
      ],
      "fields": [
        "lith_id",
        "lith",
        "lith_type",
        "lith_class",
        "lith_color"
      ]
    }
  },
  "/defs/lithology_attributes": {
    "description": "Returns lithology attribute definitions",
    "parent": "definitions",
    "visible": true,
    "options": {
      "parameters": {
        "lith_att_id": "integer, one or more lithology attribute ids",
        "att_type": "string, lithology attribute type",
        "lith_att": "string, lithology attribute",
        "all": "return all lithology attribute definitions",
        "format": "Desired output format"
      },
      "output_formats": [
        "json",
        "csv"
      ],
      "examples": [
        "api/v2/defs/lithology_attributes?all",
        "api/v2/defs/lithology_attributes?lith_type=bedform",
        "api/v2/defs/lithology_attributes?lith_att_id=3,4,5"
      ],
      "fields": [
        "lith_att_id",
        "lith_att",
        "att_type"
      ]
    }
  },
  "/defs/columns": {
    "description": "Returns column definitions",
    "parent": "definitions",
    "visible": true,
    "options": {
      "parameters": {
        "col_id": "integer, one or more column ids",
        "col_group_id": "integer, one ore more column group ids",
        "col_name": "string, column name",
        "status": "string, status of column, values 'active','in process','obsolete'",
        "all": "Return all column definitions",
        "format": "Desired output format"
      },
      "output_formats": [
        "json",
        "csv"
      ],
      "examples": [
        "api/v2/defs/columns?all",
        "api/v2/defs/columns?col_group_id=17",
        "api/v2/defs/columns?col_name=Eastern%20Kentucky"
      ],
      "fields": [
        "col_id",
        "col_group_id",
        "col_name",
        "ref_id",
        "status"
      ]
    }
  },
  "/defs/econs": {
    "description": "Returns econ definitions",
    "parent": "definitions",
    "visible": true,
    "options": {
      "parameters": {
        "econ_id": "econ identifier",
        "econ": "name of an econ",
        "econ_type": "econ type",
        "econ_class": "an econ class",
        "all": "return all environment definitions",
        "format": "Desired output format"
      },
      "output_formats": [
        "json",
        "csv"
      ],
      "examples": [
        "api/v2/defs/econs?all",
        "api/v2/defs/econs?econ_type=hydrocarbon"
      ],
      "fields": [
        "econ_id",
        "econ",
        "econ_type",
        "econ_class"
      ]
    }
  },
  "/defs/environments": {
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
      "output_formats": [
        "json",
        "csv"
      ],
      "examples": [
        "api/v2/defs/environments?all",
        "api/v2/defs/environments?environ=sand%20shoal"
      ],
      "fields": [
        "environ_id",
        "environ",
        "environ_type",
        "environ_class"
      ]
    }
  },
  "/defs/intervals": {
    "description": "Returns all time interval definitions",
    "parent": "definitions",
    "visible": true,
    "options": {
      "parameters": {
        "int_id": "integer, one or more comma-separated interval IDs",
        "all": "return all interval definitions",
        "t_age": "integer, a late age",
        "b_age": "integer, an early age",
        "rule": "if 'loose' provided along with an early_age and late_age, changes the querying of intervals",
        "age": "integer, an age - will find all intervals that overlap with this age",
        "timescale": "string, a valid timescale name as defined in /api/v2/defs/timescales",
        "timescale_id": "integer, a valid timescale_id as defined in /api/v2/defs/timescales",
        "format": "Desired output format"
      },
      "output_formats": [
        "json",
        "csv"
      ],
      "examples": [
        "api/v2/defs/intervals?all",
        "api/v2/defs/intervals?id=366",
        "api/v2/defs/intervals?timescale=new%20zealand%20ages",
        "api/v2/defs/intervals?late_age=0&early_age=130",
        "api/v2/defs/intervals?timescale_id=1&age=100"
      ],
      "fields": [
        "int_id",
        "name",
        "abbrev",
        "t_age",
        "b_age",
        "type",
        "color",
        "timescale_id"
      ]
    }
  },
  "/defs/strat_names": {
    "description": "Returns strat names",
    "parent": "definitions",
    "visible": true,
    "options": {
      "parameters": {
        "id": "unique id",
        "strat_name": "lithostratigraphic name, exact match",
        "strat_name_like": "lithostratigraphic name, with open-ended string matching",
        "rank": "lithostratigraphic rank",
        "all": "return all lithostratigraphic names",
        "format": "Desired output format"
      },
      "output_formats": [
        "json",
        "csv"
      ],
      "examples": [
        "api/v2/defs/strat_names?all",
        "api/v2/defs/strat_names?rank=Fm"
      ],
      "fields": [
        "strat_name",
        "rank",
        "strat_name_id",
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
        "b_age",
        "t_age",
        "gsc_lexicon"
      ]
    }
  },
  "/defs/timescales": {
    "description": "Returns timescales used by Macrostrat",
    "parent": "definitions",
    "visible": true,
    "options": {
      "parameters": {
        "all": "return all available timescales",
        "format": "Desired output format"
      },
      "output_formats": [
        "json",
        "csv"
      ],
      "examples": [
        "api/v2/defs/timescales?all"
      ],
      "fields": [
        "timescale_id",
        "timescale",
        "ref_id"
      ]
    }
  },
  "/defs/projects": {
    "description": "Returns available Macrostrat projects",
    "parent": "definitions",
    "visible": true,
    "options": {
      "parameters": {
        "all": "return all available projects",
        "format": "Desired output format"
      },
      "output_formats": [
        "json",
        "csv"
      ],
      "examples": [
        "api/v2/defs/timescales?all"
      ],
      "fields": [
        "project_id",
        "project",
        "timescale_id"
      ]
    }
  },
  "/defs/measurements": {
    "description": "Returns all measurements definitions",
    "parent": "definitions",
    "visible": true,
    "options": {
      "parameters": {
        "measure_id": "integer, one or more comma-separted measurement IDs",
        "measurement_class": "string, measurement_class",
        "measurement_type": "string, measurement_type",
        "all": "return all measurement definitions"
      },
      "output_formats": [
        "json",
        "csv"
      ],
      "examples": [
        "api/v2/defs/measurements?measure_id=3,4",
        "api/v2/defs/measurements?all",
        "api/v2/defs/measurements?measurement_class=geochemical"
      ],
      "fields": [
        "measure_id",
        "measurement_class",
        "measurement_type",
        "measurement"
      ]
    }
  },
  "/defs/groups": {
    "description": "Returns all column groups",
    "parent": "definitions",
    "visible": true,
    "options": {
      "parameters": {
        "all": "return all column groups"
      },
      "output_formats": [
        "json",
        "csv"
      ],
      "examples": [
        "api/v2/defs/groups?all"
      ],
      "fields": [
        "col_group_id",
        "col_group"
      ]
    }
  },
  "/defs/refs": {
    "description": "Returns references",
    "parent": "definitions",
    "visible": true,
    "options": {
      "parameters": {
        "ref_id": "integer, one or more comma-separted reference ids",
        "all": "return all references"
      },
      "output_formats": [
        "json",
        "csv"
      ],
      "examples": [
        "api/v2/defs/groups?all"
      ],
      "fields": [
        "ref_id",
        "pub_year",
        "author",
        "ref",
        "doi",
        "url"
      ]
    }
  },
  "/section_stats": {
    "description": "Return section stats for Macrostrat",
    "visible": true,
    "options": {
      "parameters": {
        "all": "return all section stats",
        "format": "Desired output format"
      },
      "output_formats": [
        "json",
        "csv"
      ],
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
        "FO_age",
        "LO_age",
        "b_age",
        "t_age"
      ]
    }
  },
  "/paleogeography": {
    "description": "Returns paleogeography geometry from http://www.gplates.org, courtesy of Mark Turner and Mike Gurnis. Note that for complete and recent reconstructions, original GPlates data services should be used - http://gplates.gps.caltech.edu:8080. If you use this service and provide attribution, you should cite GPlates via this service.",
    "visible": true,
    "options": {
      "parameters": {
        "age": "Can be between 0 and 550",
        "interval_name": "A named time interval",
        "format": "Desired output format"
      },
      "output_formats": [
        "geojson",
        "geojson_bare",
        "topojson",
        "topojson_bare"
      ],
      "examples": [
        "api/paleogeography?interval_name=Permian",
        "api/paleogeography?age=271&format=topojson"
      ],
      "fields": [
        "plateid"
      ]
    }
  },
  "/geologic_units/gmna": {
    "description": "Geologic map units. Continental-scale North American map data (gmna) adapted from the 2005 Geologic Map of North America (http://ngmdb.usgs.gov/gmna/)",
    "visible": true,
    "parent": "geologic_units",
    "options": {
      "parameters": {
        "lat": "A valid latitude",
        "lng": "A valid longitude",
        "gid": "integer, a polygon GID to search for",
        "interval_name": "string, a valid interval name as defined in /defs/intervals",
        "shape": "string, a valid WKT shape",
        "buffer": "integer, buffers a provided shape by x kilometers",
        "format": "Desired output format"
      },
      "output_formats": [
        "json",
        "csv",
        "geojson",
        "geojson_bare",
        "topojson",
        "topojson_bare"
      ],
      "examples": [
        "/api/v2/geologic_units/gmna?lat=43&lng=-89.3",
        "/api/v2/geologic_units/gmna?lat=43&lng=-89&format=geojson_bare",
        "/api/v2/geologic_units/gmna?interval_name=Permian",
        "/api/v2/geologic_units/gmna?shape=LINESTRING(-88 43,-90 43)&buffer=20"
      ],
      "fields": [
        "gid",
        "unit_abbre",
        "rocktype",
        "lithology",
        "lith_type",
        "lith_class",
        "t_interval",
        "t_age",
        "b_interval",
        "b_age",
        "containing_interval",
        "color"
      ]
    }
  },
  "/geologic_units/gmus": {
    "description": "Geologic map units. State-level (gmus) data adapated from http://mrdata.usgs.gov/geology/state/.",
    "visible": true,
    "parent": "geologic_units",
    "options": {
      "parameters": {
        "gid": "integer, a polygon GID to search for",
        "lat": "A valid latitude in decimal degrees",
        "lng": "A valid longitude in decimal degrees",
        "strat_name_id": "integer, one or more valid strat_name_ids from /defs/strat_names",
        "unit_id": "integer, one or more valid unit_ids from /units",
        "search": "string, a term to search for in GMUS metadata",
        "shape": "string, a valid WKT shape",
        "buffer": "integer, buffers a provided shape by x kilometers",
        "unit_link": "string, GMUS unit_link",
        "interval_name": "string, a valid interval name as defined in /defs/intervals",
        "format": "Desired output format"
      },
      "output_formats": [
        "json",
        "csv",
        "geojson",
        "geojson_bare",
        "topojson",
        "topojson_bare"
      ],
      "examples": [
        "/api/v2/geologic_units/gmus?lat=43&lng=-89.3",
        "/api/v2/geologic_units/gmus?lat=43&lng=-89&format=geojson_bare",
        "/api/v2/geologic_units/gmus?interval_name=Permian",
        "/api/v2/geologic_units/gmus?shape=LINESTRING(-88 43,-90 43)&buffer=20"
      ],
      "fields": [
        "gid",
        "area",
        "unit_link",
        "interval_color",
        "lithology",
        "rocktype",
        "macro_units",
        "strat_names",
        "t_interval",
        "t_age",
        "b_interval",
        "b_age",
        "containing_interval",
        "unit_com",
        "unit_name",
        "unitdesc",
        "strat_unit",
        "color"
      ]
    }
  },
  "/mobile": {
    "description": "Simplified data delivery, ideal for mobile applications",
    "visible": true
  },
  "/mobile/point": {
    "description": "Get state-level map (gmus) unit and Macrostrat polygon for a given point",
    "parent": "mobile",
    "visible": true,
    "options": {
      "parameters": {
        "lat": "A valid latitude",
        "lng": "A valid longitude",
        "geo_format": "Output geometry format - can be 'wkt' or 'geojson'; Defaults to 'geojson'"
      },
      "output_formats": [
        "json"
      ],
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
  },
  "/mobile/point_details": {
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
      "output_formats": [
        "json"
      ],
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
  },
  "/mobile/fossil_collections": {
    "description": "Get Paleobiology Database (http://paleobiodb.org) fossil collection numbers matched to a given Macrostrat unit",
    "parent": "mobile",
    "visible": true,
    "options": {
      "parameters": {
        "unit_id": "Macrostrat unit ID"
      },
      "output_formats": [
        "json"
      ],
      "examples": [
        "/mobile/fossil_collections?unit_id=6132"
      ],
      "fields": [
        "cltn_id",
        "cltn_name"
      ]
    }
  },
  "/editing": {
    "description": "Routes for updating Macrostrat data",
    "visible": false
  },
  "/editing/map": {
    "description": "WILL BE DEPRECATED. Fetch polygons for mapping",
    "parent": "editing",
    "visible": false
  },
  "/editing/map/update": {
    "description": "Update column polygon geometry",
    "parent": "editing",
    "visible": false
  },
  "/editing/section": {
    "description": "Update sections",
    "parent": "editing",
    "visible": false
  },
  "/editing/units/update": {
    "description": "Update units",
    "parent": "editing",
    "visible": false
  },
  "define": {
    "id": "integer, unique identifier",
    "col_group": "text, name of group the column belongs to, generally corresponds to geologic provinces",
    "col_group_id": "integer, unique identifier for column group",
    "col_id": "integer, unique identifier for column",
    "col_name": "text, name of column",
    "columns": "integer, number of columns",
    "unit_id": "integer, unique identifier for unit",
    "section_id": "integer, unique identifier for section (package)",
    "sections": "int[], section_ids that belong to group",
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
    "min_thick": "number, minimum thickess in meters (NB: some zero values may be equivalent in meaning to NULL)",
    "color": "text, recommended coloring for units based on dominant lithology",
    "u_color": "text, original color for unit",
    "text_color": "text, recommended coloring for text based on color",
    "FO_interval": "text, chronostratigraphic interval containing initiation/earliest(oldest) age",
    "FO_age": "number, age of FO_interval base in Myr before present",
    "b_interval": "integer, chronostratigraphic interval containing continuous time age model oldest boundary",
    "b_age": "number, continuous time age model estimated for initiation, in Myr before present",
    "b_prop": "decimal, position of continuous time age model bottom boundary, proportional to reference time interval (b_interval)",
    "early_age": "number, oldest age, Myr before present",
    "LO_interval": "text, chronostratigraphic interval containing truncation/latest(youngest) age",
    "LO_age": "number, age of FO_interval top in Myr before present",
    "t_age": "number, continuous time age model estimated for truncation, in Myr before present",
    "t_interval": "integer, chronostratigraphic interval containing continuous time age model youngest boundary",
    "t_prop": "decimal, position of continuous time age model top boundary, proportional to reference time interval (t_interval)",
    "late_age": "number, youngest age, Myr before present",
    "position_bottom": "number, estimated position of unit relative to other units in section",
    "lith": "text, specific lithology, see /defs/lithologies",
    "lith_type": "text, general lithology type, see /defs/lithologies",
    "lith_class": "text, general lithology class, see /defs/lithologies",
    "measurement": "text, specific measurement",
    "measurement_type": "text, general measurement type",
    "measurement_class": "text, general measurement class",
    "lith_max_thick": "number, thickness of specified lithology, based on proportion of unit(s)",
    "lith_min_thick": "number, thickness of specified lithology, based on proportion of unit(s)",
    "environ": "text, specific environment, see /defs/environments",
    "environ_type": "general environment type, /defs/environments",
    "environ_class": "text, general lithology class, /defs/environments",
    "outcrop": "text, describes where unit is exposed or not, values are  'outcrop', 'subsurface', or 'both'",
    "pbdb": "number of matching Paleobiology Database fossil collections",
    "units": "integer, number of units",
    "notes": "text, notes releavnt to containing element",
    "project": "text, name of project",
    "status": "text, indicates current status of column, values are 'active', 'in process', 'obsolete'",
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
    "timescale_id": "integer, unique identifier for timescale used in project",
    "top": "text, named time interval that contains the top of the section",
    "top_age": "number, minimum age of the section in millions of years",
    "bottom": "text, named time interval that contains the bottom of the section",
    "bottom_age": "number, maximum age of the section in millions of years",
    "abbrev": "standard abbreviation for interval name",
    "gsc_lexicon": "Canada Geological Survey Lexicon web id; data for some names can be accessed via link: http://weblex.nrcan.gc.ca/html/000000/GSCC00053000747.html",
    "clat": "number, present day latitude of of the centroid of the column to which the unit belongs",
    "clng": "number, present day longitude of of the centroid of the column to which the unit belongs",
    "t_plat": "number, same as clat, but rotated to the t_age. Top age paleo latitude.",
    "t_plng": "number, same as clng, but rotated to the t_age. Top age paleo longitude.",
    "b_plat": "number, same as clat, but rotated to the b_age. Bottom age paleo latitude.",
    "b_plng": "number, same as clng, but rotated to the b_age. Bottom age paleo latitude.",
    "econ_id": "integer, unique econ identifier, see defs/econs",
    "econ": "text, name of econonomic use, see defs/econs",
    "econ_type": "string, type of econonomic use, see defs/econs",
    "econ_class": "text, class of econonomic use, see defs/econs",
    "ref_id": "integer, unique reference identifer",
    "ref": "text, name of reference"
  }
}; 
  module.exports = defs; 
}());