(function() {
  var defs = {
  "/columns": {
    "description": "Search and summarize columns based on unit properties or geographic location",
    "visible": true,
    "options": {
      "parameters": {
        "unit_id": "integer, a valid unit id",
        "section_id": "integer, a valid section id",
        "col_id": "integer, a valid column id",
        "col_type": "string, a column type",
        "interval_name": "string, chronostratigraphic time interval name",
        "int_id": "integer, a chronostratigraphic time interval ID from /defs/intervals",
        "age": "numerical age in millions of years before present",
        "age_top": "numerical age (Ma) - must be used with age_bottom and be less than age_bottom",
        "age_bottom": "numerical age (Ma) - must be used with age_top and be greater than age_top",
        "lith_id": "integer, ID of a lithology from /defs/lithologies",
        "lith": "string, specific lithology name (e.g., shale, sandstone)",
        "lith_type": "string, groups of lithologies (e.g., carbonate, siliciclastic)",
        "lith_class": "string, general lithologies (sedimentary, igneous, metamorphic)",
        "lith_att_id": "integer, ID of a lithology attribute from /defs/lithology_attributes",
        "lith_att": "string, specific lithology attribute name (e.g. fine, olivine, poorly washed)",
        "lith_att_type": "string, specific category of lithology attribute (e.g. grains, lithology, bedform)",
        "environ_id": "integer, specific environment ID from /defs/environments",
        "environ": "string, specific environment",
        "environ_type": "string, groups of environments",
        "environ_class": "string, general environments",
        "econ_id": "integer, ID of an economic attribute from /defs/econs",
        "econ": "string, name of an economic attribute",
        "econ_type": "string, name of an economic attribute type",
        "econ_class": "string, name of an economic attribute class",
        "cltn_id": "integer, one or more Paleobiology Database collection IDs",
        "strat_name": "a fuzzy stratigraphic name to match units to",
        "strat_name_id": "integer, a single or comma-separated list of stratigraphic IDs from /defs/strat_names",
        "lat": "number, decimal degree latitude, WGS84",
        "lng": "number, decimal degree longitude, WGS84",
        "adjacents": "boolean, if lat/lng or col_id is specified, optionally return all units in columns that touch the polygon containing the supplied lat/lng",
        "project_id": "a Macrostrat project ID",
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
        "lat",
        "lng",
        "col_group",
        "col_group_id",
        "group_col_id",
        "col_area",
        "project_id",
        "max_thick",
        "max_min_thick",
        "min_min_thick",
        "b_age",
        "t_age",
        "pbdb_collections",
        "lith",
        "environ",
        "econ",
        "t_units",
        "t_sections"
      ]
    }
  },
  "/sections": {
    "description": "Summarize units by gap-bound packages",
    "visible": true,
    "options": {
      "parameters": {
        "unit_id": "integer, a valid unit id",
        "section_id": "integer, a valid section id",
        "col_id": "integer, a valid column id",
        "interval_name": "string, chronostratigraphic time interval name",
        "int_id": "integer, a chronostratigraphic time interval ID from /defs/intervals",
        "age": "numerical age in millions of years before present",
        "age_top": "numerical age (Ma) - must be used with age_bottom and be less than age_bottom",
        "age_bottom": "numerical age (Ma) - must be used with age_top and be greater than age_top",
        "lith_id": "integer, ID of a lithology from /defs/lithologies",
        "lith": "string, specific lithology name (e.g., shale, sandstone)",
        "lith_group": "string, group of lithologies (e.g., unconsolidated)",
        "lith_type": "string, type of lithologies (e.g., carbonate, siliciclastic)",
        "lith_class": "string, general lithologies (sedimentary, igneous, metamorphic)",
        "lith_att_id": "integer, ID of a lithology attribute from /defs/lithology_attributes",
        "lith_att": "string, specific lithology attribute name (e.g. fine, olivine, poorly washed)",
        "lith_att_type": "string, specific category of lithology attribute (e.g. grains, lithology, bedform)",
        "environ_id": "integer, specific environment ID from /defs/environments",
        "environ": "string, specific environment",
        "environ_type": "string, groups of environments",
        "environ_class": "string, general environments",
        "econ_id": "integer, ID of an economic attribute from /defs/econs",
        "econ": "string, name of an economic attribute",
        "econ_type": "string, name of an economic attribute type",
        "econ_class": "string, name of an economic attribute class",
        "cltn_id": "integer, one or more Paleobiology Database collection IDs",
        "strat_name": "a fuzzy stratigraphic name to match units to",
        "strat_name_id": "integer, a single or comma-separated list of stratigraphic IDs from /defs/strat_names",
        "lat": "number, decimal degree latitude, WGS84",
        "lng": "number, decimal degree longitude, WGS84",
        "adjacents": "boolean, if lat/lng or col_id is specified, optionally return all units in columns that touch the polygon containing the supplied lat/lng",
        "project_id": "a Macrostrat project ID",
        "response": "Any available response_type. Default is short.",
        "format": "string, desired output format"
      },
      "output_formats": [
        "json",
        "csv"
      ],
      "response_types": [
        "short",
        "long"
      ],
      "examples": [
        "/api/sections?all",
        "/api/sections?col_id=49"
      ],
      "fields": [
        "col_id",
        "col_area",
        "section_id",
        "project_id",
        "max_thick",
        "min_thick",
        "t_age",
        "b_age",
        "pbdb_collections",
        "lith",
        "environ",
        "econ",
        "name",
        "type",
        "class"
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
        "col_type": "string, a column type",
        "interval_name": "string, chronostratigraphic time interval name",
        "int_id": "integer, a chronostratigraphic time interval ID from /defs/intervals",
        "age": "numerical age in millions of years before present",
        "age_top": "numerical age (Ma) - must be used with age_bottom and be less than age_bottom",
        "age_bottom": "numerical age (Ma) - must be used with age_top and be greater than age_top; note that returned units may not be entirely contained by age_top and age_bottom, but they will intersect that age range in whole or in part",
        "lith_id": "integer, ID of a lithology from /defs/lithologies",
        "lith": "string, specific lithology name (e.g., shale, sandstone)",
        "lith_group": "string, groups of lithologies (e.g., sandstones, mudrocks, unconsolidated)",
        "lith_type": "string, types of lithologies (e.g., carbonate, siliciclastic)",
        "lith_class": "string, general lithologies (sedimentary, igneous, metamorphic)",
        "lith_att_id": "integer, ID of a lithology attribute from /defs/lithology_attributes",
        "lith_att": "string, specific lithology attribute name (e.g. fine, olivine, poorly washed)",
        "lith_att_type": "string, specific category of lithology attribute (e.g. grains, lithology, bedform)",
        "environ_id": "integer, specific environment ID from /defs/environments",
        "environ": "string, specific environment",
        "environ_type": "string, groups of environments",
        "environ_class": "string, general environments",
        "econ_id": "integer, ID of an economic attribute from /defs/econs",
        "econ": "string, name of an economic attribute",
        "econ_type": "string, name of an economic attribute type",
        "econ_class": "string, name of an economic attribute class",
        "cltn_id": "integer, one or more Paleobiology Database collection IDs",
        "strat_name": "a fuzzy stratigraphic name to match units to",
        "strat_name_id": "integer, a single or comma-separated list of stratigraphic IDs from /defs/strat_names",
        "lat": "number, decimal degree latitude, WGS84",
        "lng": "number, decimal degree longitude, WGS84",
        "adjacents": "boolean, if lat/lng or col_id is specified, optionally return all units in columns that touch the polygon containing the supplied lat/lng",
        "project_id": "a Macrostrat project ID",
        "response": "Any available response_type. Default is short.",
        "geom_age": "If requesting a geographic format, specifies which age to use for the primary coordinates. Accepted parameters are 'modern' (clat, clng), 'top' (t_plat, t_plng) and 'bottom' (b_plat, b_plng). Default is 'modern'",
        "summarize_measures": "If present, returns summary statistics about the measurements associated with each unit",
        "show_position": "If present, return the unit top and bottom position in section",
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
        "topojson",
        "geojson_bare",
        "topojson_bare"
      ],
      "examples": [
        "api/units?section_id=107&format=csv",
        "api/units?interval_name=Permian",
        "api/units?age=271",
        "api/units?interval_name=Permian&response=long",
        "api/units?strat_id=1205,4260",
        "api/units?strat_name=mancos",
        "api/units?strat_name_id=1205&format=geojson_bare&geom_age=bottom"
      ],
      "fields": [
        "unit_id",
        "section_id",
        "col_id",
        "project_id",
        "col_area",
        "unit_name",
        "strat_name_id",
        "Mbr",
        "Fm",
        "Gp",
        "SGp",
        "t_age",
        "b_age",
        "max_thick",
        "min_thick",
        "outcrop",
        "pbdb_collections",
        "pbdb_occurrences",
        "lith",
        "environ",
        "econ",
        "measure",
        "notes",
        "color",
        "text_color",
        "t_int_id",
        "t_int_name",
        "t_int_age",
        "t_prop",
        "units_above",
        "b_int_id",
        "b_int_name",
        "b_int_age",
        "b_prop",
        "units_below",
        "clat",
        "clng",
        "t_plat",
        "t_plng",
        "b_plat",
        "b_plng",
        "t_pos",
        "b_pos"
      ]
    }
  },
  "/fossils": {
    "description": "Paleobiology Database (http://paleobiodb.org) collections matched to Macrostrat units",
    "visible": true,
    "options": {
      "parameters": {
        "interval_name": "string, chronostratigraphic time interval name",
        "age": "numerical age in millions of years before present",
        "age_top": "numerical age (Ma) - must be used with age_bottom and be less than age_bottom",
        "age_bottom": "numerical age (Ma) - must be used with age_top and be greater than age_top",
        "lith_id": "integer, ID of a lithology from /defs/lithologies",
        "lith": "string, specific lithology name (e.g., shale, sandstone)",
        "lith_type": "string, groups of lithologies (e.g., carbonate, siliciclastic)",
        "lith_class": "string, general lithologies (sedimentary, igneous, metamorphic)",
        "environ_id": "integer, specific environment ID from /defs/environments",
        "environ": "string, specific environment",
        "environ_type": "string, groups of environments",
        "environ_class": "string, general environments",
        "econ_id": "integer, ID of an economic attribute from /defs/econs",
        "econ": "string, name of an economic attribute",
        "econ_type": "string, name of an economic attribute type",
        "econ_class": "string, name of an economic attribute class",
        "unit_id": "One or more comma-separated valid unit IDs",
        "col_id": "One or more comma-separated valid column IDs",
        "project_id": "One or more comma-separated valid project IDs",
        "strat_name_id": "One or more comma-separted valid strat_name_ids from /defs/strat_names",
        "strat_name_concept_id": "One or more stratigraphic name concepts from /defs/strat_name_concepts",
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
        "/api/fossils?interval_name=Permian",
        "/api/fossils?age=271",
        "/api/fossils?age_top=200&age_bottom=250",
        "/api/fossils?col_id=446"
      ],
      "fields": [
        "cltn_id",
        "cltn_name",
        "pbdb_occs",
        "genus_no",
        "unit_id",
        "col_id",
        "t_age",
        "b_age"
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
    "visible": true,
    "isParent": true
  },
  "/defs/autocomplete": {
    "description": "Quickly retrieve all definitions matching a query. Limited to 100 results.",
    "parent": "definitions",
    "visible": true,
    "options": {
      "parameters": {
        "query": "The search term",
        "include": "Definitions to include",
        "exclude": "Definitions to exclude"
      },
      "output_formats": [
        "json"
      ],
      "examples": [
        "api/v2/defs/autocomplete?query=Mancos",
        "api/v2/defs/autocomplete?query=Waldron&exclude=lithologies,lithology_attributes"
      ],
      "fields": [
        "intervals",
        "strat_name_concepts",
        "strat_name_orphans",
        "columns",
        "lithology_attributes",
        "lithologies",
        "id",
        "name"
      ]
    }
  },
  "/defs/define": {
    "description": "Define multiple terms simultaneously",
    "parent": "definitions",
    "visible": true,
    "options": {
      "parameters": {
        "col_id": "columns",
        "econ_id": "econs",
        "econ_type": "econs",
        "econ_class": "econs",
        "environ_id": "environments",
        "environ_type": "environments",
        "environ_class": "environments",
        "col_group_id": "groups",
        "int_id": "intervals",
        "lith_id": "lithologies",
        "lith_type": "lithologies",
        "lith_class": "lithologies",
        "lith_att_id": "lithology_attributes",
        "strat_name_id": "strat_names",
        "strat_name_concept_id": "strat_name_concepts",
        "timescale_id": "timescales"
      },
      "output_formats": [
        "json"
      ],
      "examples": [
        "api/v2/defs/define?strat_name_concept_id=9165&lith_id=1&int_id=751,123"
      ],
      "fields": [
        "columns",
        "econs",
        "environments",
        "groups",
        "intervals",
        "lithologies",
        "lithology_attributes",
        "strat_names",
        "strat_name_concepts",
        "timescales"
      ]
    }
  },
  "/defs/languages": {
    "description": "Returns ISO 639-3 and ISO 639-1 codes for all languages",
    "parent": "definitions",
    "visible": true,
    "options": {
      "parameters": {
        "name": "string, the name of a language",
        "code": "string, an ISO 639-3 or ISO 639-1 language code",
        "all": "return all language definitions"
      },
      "output_formats": [
        "json",
        "csv"
      ],
      "examples": [
        "api/v2/defs/languages?name=hawaiian",
        "api/v2/defs/languages?code=hmn,jpn,ita",
        "api/v2/defs/languages?all"
      ],
      "fields": [
        "name",
        "iso639_3",
        "iso639_1"
      ]
    }
  },
  "/defs/lithologies": {
    "description": "Returns all lithology definitions",
    "parent": "definitions",
    "visible": true,
    "options": {
      "parameters": {
        "lith_id": "integer, one or more lithology ids",
        "lith": "string, lithology",
        "lith_group": "string, lithology group",
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
        "name",
        "group",
        "type",
        "class",
        "color"
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
        "api/v2/defs/lithology_attributes?lith_att=bedform",
        "api/v2/defs/lithology_attributes?lith_att_id=3,4,5"
      ],
      "fields": [
        "lith_att_id",
        "name",
        "type"
      ]
    }
  },
  "/defs/structures": {
    "description": "Returns all structure definitions",
    "parent": "definitions",
    "visible": true,
    "options": {
      "parameters": {
        "structure_id": "integer, one or more structure ids",
        "structure": "string, structure",
        "structure_like": "string, loose match to structure",
        "structure_group": "string, structure group",
        "structure_class": "string, structure class",
        "structure_type": "string, structure type",
        "all": "return all structure definitions"
      },
      "output_formats": [
        "json",
        "csv"
      ],
      "examples": [
        "api/v2/defs/structures?structure_id=3",
        "api/v2/defs/structures?all",
        "api/v2/defs/structures?structure_class=fabric"
      ],
      "fields": [
        "structure_id",
        "name",
        "group",
        "type",
        "class"
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
        "col_group_id": "integer, one or more column group ids",
        "col_name": "string, column name",
        "project_id": "integer, one or more project ids",
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
        "lat",
        "lng",
        "col_area",
        "project_id",
        "t_units",
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
        "name",
        "type",
        "class",
        "color"
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
        "name",
        "type",
        "class",
        "color"
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
        "t_age": "integer, a late age in Ma",
        "b_age": "integer, an early age in Ma",
        "name": "string, interval name",
        "true_colors": "boolean, returns original international time scale colors",
        "rule": "if 'loose' provided along with an early_age and late_age, changes the querying of intervals",
        "age": "integer, an age in Ma - will find all intervals that overlap with this age",
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
        "int_type",
        "color",
        "timescales"
      ]
    }
  },
  "/defs/sources": {
    "description": "Returns sources associated with geologic units. If a geographic format is requested, the bounding box of the source is returned as the geometry.",
    "parent": "definitions",
    "visible": true,
    "options": {
      "parameters": {
        "source_id": "integer, one or more comma-separated source IDs",
        "scale": "string, one or more comma-separated Burwell scales (tiny, small, medium, large)",
        "lat": "A valid latitude",
        "lng": "A valid longitude",
        "shape": "string, a WKT geometry that can be used to filter sources",
        "buffer": "integer, buffer in meters that should be applied to a provided shape",
        "all": "return all source definitions",
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
        "api/v2/defs/sources?all",
        "api/v2/defs/sources?source_id=1,2,3",
        "api/v2/defs/sources?shape=LINESTRING(-122.3438%2037,-89.3527%2043.0582)&buffer=100",
        "api/v2/defs/sources?lat=43.03&lng=-89.4&scale=large"
      ],
      "fields": [
        "source_id",
        "name",
        "url",
        "ref_title",
        "authors",
        "ref_year",
        "ref_source",
        "isbn_doi",
        "scale"
      ]
    }
  },
  "/defs/strat_names": {
    "description": "Returns strat names",
    "parent": "definitions",
    "visible": true,
    "options": {
      "parameters": {
        "strat_name_id": "unique id",
        "strat_name": "lithostratigraphic name, exact match",
        "strat_name_like": "lithostratigraphic name, with open-ended string matching",
        "concept_id": "uniqe id for stratigraphic concepts",
        "rank": "lithostratigraphic rank",
        "rule": "Can be 'all' or 'down'. Down will return any children of the requested stratigraphic name, and all will return the entire stratigraphic name hierarchy that the request name belongs to",
        "interval_name": "chronostratigrpahic interval name (see /defs/intervals); this will return only strat_names with a declared age in Macrostrat",
        "ref_id": "retrieve only stratigraphic names linked the specified reference_id (see /defs/refs)",
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
        "concept_id",
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
        "ref_id"
      ]
    }
  },
  "/defs/strat_name_concepts": {
    "description": "Returns strat name concepts",
    "parent": "definitions",
    "visible": true,
    "options": {
      "parameters": {
        "concept_id": "unique id",
        "concept_name": "string specifying concept name",
        "all": "return all lithostratigraphic names",
        "format": "Desired output format"
      },
      "output_formats": [
        "json",
        "csv"
      ],
      "examples": [
        "api/v2/defs/concept_id?all"
      ],
      "fields": [
        "concept_id",
        "name",
        "geologic_age",
        "int_id",
        "b_int_id",
        "t_int_id",
        "usage_notes",
        "other",
        "province",
        "url",
        "authors",
        "ref_id"
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
        "max_age",
        "min_age",
        "n_intervals",
        "ref_id"
      ]
    }
  },
  "/defs/minerals": {
    "description": "Returns mineral names and formulas",
    "parent": "definitions",
    "visible": true,
    "options": {
      "parameters": {
        "all": "return all available minerals",
        "mineral": "string, name of mineral",
        "mineral_type": "string, type of mineral (e.g., feldspar)",
        "element": "string, chemical element abbreviation, case sensitive (e.g., Co)",
        "format": "Desired output format"
      },
      "output_formats": [
        "json",
        "csv"
      ],
      "examples": [
        "api/v2/defs/minerals?all",
        "api/v2/defs/minerals?mineral_id=1",
        "api/v2/defs/minerals?mineral_type=clinopyroxene",
        "api/v2/defs/minerals?element=Co"
      ],
      "fields": [
        "mineral_id",
        "mineral",
        "mineral_type",
        "hardness_min",
        "hardness_max",
        "mineral_color",
        "lustre",
        "crystal_form",
        "formula",
        "formula_tags",
        "url"
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
        "project_id": "integer identifying project(s), separate multiple values with commas",
        "format": "Desired output format"
      },
      "output_formats": [
        "json",
        "csv"
      ],
      "examples": [
        "api/v2/defs/projects?all"
      ],
      "fields": [
        "project_id",
        "project",
        "decrip",
        "timescale_id",
        "t_cols",
        "t_units"
      ]
    }
  },
  "/defs/plates": {
    "description": "Returns definitions of plates from /paleogeography",
    "parent": "definitions",
    "visible": true,
    "options": {
      "parameters": {
        "all": "return all available projects",
        "plate_id": "One or more plate_ids to query",
        "format": "Desired output format"
      },
      "output_formats": [
        "json",
        "csv"
      ],
      "examples": [
        "api/v2/defs/plates?all",
        "api/v2/defs/plates?plate_id=129,402"
      ],
      "fields": [
        "plate_id",
        "name"
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
        "name",
        "type",
        "class",
        "t_units"
      ]
    }
  },  "/defs/measurement_sources": {
      "description": "Returns references used in Macrostrat measurements",
      "parent": "definitions",
      "visible": false,
      "options": {
        "parameters": {
          "doi": "string, a specific doi, note that it is necessary to use one DOI at a time in this query",
          "measurement_class": "string, measurement_class",
          "measurement_type": "string, measurement_type",
          "measurement": "string, measurement",
          "all": "return all measurement definitions"
        },
        "output_formats": [
          "json",
          "csv"
        ],
        "examples": [
          "api/v2/defs/measurement_sources?doi=10.1016/j.epsl.2009.11.039",
          "api/v2/defs/measurements?all",
          "api/v2/defs/measurements?measurement_class=geochemical"
        ],
        "fields": [
          "ref_id",
          "pub_year",
          "author",
          "ref",
          "doi",
          "url",
          "measurements"
        ]
      }
    },
  "/defs/groups": {
    "description": "Returns all column groups",
    "parent": "definitions",
    "visible": true,
    "options": {
      "parameters": {
        "all": "return all column groups",
        "project_id": "limit results to specific project",
        "col_id": "get col_group data for specific column",
        "col_group_id": "get col_group data for specific col_group_id"
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
        "col_group",
        "t_units",
        "t_cols",
        "project_id",
        "name"
      ]
    }
  },
  "/defs/grainsizes": {
    "description": "Returns grain size definitions",
    "parent": "definitions",
    "visible": true,
    "options": {
      "parameters": {
        "grain_id": "Unique grain ID",
        "grain_symbol": "The grain symbol for display purposes",
        "grain_name": "The name of the grain",
        "grain_group": "The family of grains the grain belongs to",
        "soil_group": "The family of soils the grain belongs to",
        "classification": "The classification scheme the given grain belongs to",
        "all": "Return all grain sizes",
        "format": "Desired output format"
      },
      "output_formats": [
        "json",
        "csv"
      ],
      "examples": [
        "api/v2/defs/grainsizes?all",
        "api/v2/defs/grainsizes?grain_name=clay",
        "api/v2/defs/grainsizes?classification=iso"
      ],
      "fields": [
        "grain_id",
        "grain_symbol",
        "grain_group",
        "soil_group",
        "min_size",
        "max_size",
        "classification"
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
  "/defs/drilling_sites": {
    "description": "Returns metadata for offshore drilling sites from ODP, DSDP and IODP",
    "parent": "definitions",
    "visible": true,
    "options": {
      "parameters": {
        "epoch": "string, drilling 'epoch'; only three valid values. DSDP, ODP and IODP",
        "leg": "string, drilling leg (or expedition for IODP)",
        "site": "string, drilling site",
        "col_id": "integer, one or more Macrostrat column ids",
        "col_group_id": "integer, one or more Macrostrat column group ids; corresponds to legs/expeditions",
        "all": "return all drilling expeditions and sites",
        "sample": "if present, get a selection of data",
        "format": "desired output format, options given below in output_formats"
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
        "api/v2/defs/drilling_sites?format=geojson_bare",
        "api/v2/defs/drilling_sites?site=U1547",
        "api/v2/defs/drilling_sites?all",
        "api/v2/defs/drilling_sites?exp=385"
      ],
      "fields": [
        "epoch",
        "leg",
        "site",
        "hole",
        "lat",
        "lng",
        "col_id",
        "col_group_id",
        "penetration",
        "cored",
        "recovered",
        "recovery",
        "drilled_interval",
        "drilled_intervals",
        "cores",
        "date_started",
        "comments",
        "ref_id",
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
  "/measurements": {
    "description": "measurements",
    "visible": true,
    "options": {
      "parameters": {
        "measurement": "string, measurement definition name",
        "measurement_type": "string, measurement definition type",
        "measurement_class": "string, measurement definition class",
        "measurement_id": "integer, measurement definition unique identifier",
        "measure_id": "integer, specific measurement id",
        "measuremeta_id": "integer, specific id for measurment metadata (generally a sample)",
        "unit_id": "integer, one or more ids for unit containing measurements",
        "lith_id": "integer, one or more ids for lith (see /defs/lithologies)",
        "lith_type": "string, one or more lithology types",
        "lith_class": "string, one or more lithology classes",
        "section_id": "integer, id for section containing measurements",
        "col_id": "integer, id for column containing measurements",
        "project_id": "integer, id for project",
        "measure_phase": "string, phase from which measurement was taken (e.g., 'zircon')",
        "response": "Any available response_type. Default is short. Use 'light' for effecient return of measurements with little metadata",
        "format": "Desired output format",
        "sample": "if present, show a subset of the data",
        "show_values": "if present, show measurements as arrays, grouped by measuremeta_id and measurement_id"
      },
      "response_types": [
        "light",
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
        "api/measurements?col_id=11&show_values",
        "api/measurements?measure_id=353&response=long"
      ],
      "fields": [
        "measurement_id",
        "measuremeta_id",
        "measurement",
        "measure_units",
        "measure_phase",
        "method",
        "n",
        "measure_value",
        "measure_error",
        "measure_position",
        "measure_n",
        "error_units",
        "lat",
        "lng",
        "samp_geo_unit",
        "samp_lith",
        "samp_desc",
        "samp_age",
        "ref_id",
        "unit_id",
        "col_id",
        "strat_name_id",
        "match_basis",
        "ref"
      ]
    }
  },
  "/paleogeography": {
    "description": "Returns paleogeography geometry from \"Wright et al. (2013) Towards community-driven paleogeographic reconstructions: integrating open-access paleogeographic and paleobiology data with plate tectonics. Biogeosciences 10:1529-1541\"  If you use this service and provide attribution, you should cite the associated paper via this service.",
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
        "plate_id"
      ]
    }
  },
  "/geologic_units/gmna": {
    "description": "Geologic map units. Continental-scale North American map data (gmna) adapted from the 2005 Geologic Map of North America (http://ngmdb.usgs.gov/gmna/)",
    "visible": false,
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
        "lith",
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
    "visible": false,
    "parent": "geologic_units",
    "options": {
      "parameters": {
        "gid": "integer, a polygon GID to search for",
        "lat": "A valid latitude in decimal degrees",
        "lng": "A valid longitude in decimal degrees",
        "strat_name_id": "integer, one or more valid strat_name_ids from /defs/strat_names",
        "unit_id": "integer, one or more valid unit_ids from /units",
        "search": "string, a term to search for in map metadata",
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
        "t_int_id",
        "t_age",
        "b_int_id",
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
  "/geologic_units/burwell": {
    "description": "Geologic map units from various data sources",
    "visible": false,
    "parent": "geologic_units",
    "options": {
      "parameters": {
        "scale": "Can be 'small', 'medium', or 'large'",
        "map_id": "integer, one or more polygon map_ids to search for",
        "lat": "A valid latitude in decimal degrees",
        "lng": "A valid longitude in decimal degrees",
        "strat_name_id": "integer, one or more valid strat_name_ids from /defs/strat_names",
        "unit_id": "integer, one or more valid unit_ids from /units",
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
        "/api/v2/geologic_units/burwell?lat=43&lng=-89.3"
      ],
      "fields": [
        "map_id",
        "source_id",
        "name",
        "strat_name",
        "lith",
        "descrip",
        "comments",
        "macro_units",
        "strat_names",
        "t_int_id",
        "t_int_age",
        "t_int_name",
        "b_int_id",
        "b_int_age",
        "b_int_name",
        "color"
      ]
    }
  },
    "/geologic_units/map": {
      "description": "Geologic map units from various data sources",
      "visible": true,
      "parent": "geologic_units",
      "options": {
        "parameters": {
          "scale": "Can be 'small', 'medium', or 'large'",
          "map_id": "integer, one or more polygon map_ids to search for",
          "lat": "A valid latitude in decimal degrees",
          "lng": "A valid longitude in decimal degrees",
          "strat_name_id": "integer, one or more valid strat_name_ids from /defs/strat_names",
          "unit_id": "integer, one or more valid unit_ids from /units",
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
          "/api/v2/geologic_units/map?lat=43&lng=-89.3"
        ],
        "fields": [
          "map_id",
          "source_id",
          "name",
          "strat_name",
          "lith",
          "descrip",
          "comments",
          "macro_units",
          "strat_names",
          "t_int_id",
          "t_int_age",
          "t_int_name",
          "b_int_id",
          "b_int_age",
          "b_int_name",
          "color"
        ]
      }
    },
  "/geologic_units/burwell/points": {
    "description": "Query point features from geologic maps",
    "visible": false,
    "parent": "geologic_units",
    "options": {
      "parameters": {
        "point_id": "One or more comma-separated valid point_ids",
        "point_type": "One or more comma-separated point_types",
        "certainty": "A string to search the certainty field for (fuzzy)",
        "comments": "A string to search the comments field for (fuzzy)",
        "source_id": "One or more comma-separated source_ids",
        "minlat": "A minimum latitude that represents the southwest corner of a bounding box (requires minlng, maxlat, and maxlng)",
        "minlng": "A minimum longitude that represents the southwest corner of a bounding box (requires minlat, maxlat, and maxlng)",
        "maxlat": "A maximum latitude that represents the northeast corner of a bounding box (requires minlat, minlng, and maxlng)",
        "maxlng": "A maximum longitude that represents the northeast corner of a bounding box (requires minlat, minlng, and maxlat)",
        "format": "Desired output format. Default is GeoJSON",
        "sample": "Return a sample of data"
      },
      "output_formats": [
        "geojson",
        "geojson_bare",
        "topojson",
        "topojson_bare",
        "csv"
      ],
      "examples": [
        "/api/v2/geologic_units/burwell/points?point_id=1,2,3",
        "/api/v2/geologic_units/burwell/points?point_type=joint",
        "/api/v2/geologic_units/burwell/points?minlng=-112.7672&minlat=36.0627&maxlng=-112.5390&maxlat=36.1872"
      ],
      "fields": [
        "point_id",
        "strike",
        "dip",
        "dip_dir",
        "point_type",
        "certainty",
        "comments",
        "source_id"
      ]
    }
  },

  "/geologic_units/map/legend": {
    "description": "Retrieve legends for geologic map units",
    "visible": true,
    "parent": "geologic_units",
    "options": {
      "parameters": {
        "scale": "Restrict results to maps of a specific scale(s) in Macrostrat's system, can be tiny, small, medium, or large",
        "carto": "Restrict results to map components present in one of Macrostrat's map harmonized scales: tiny, small, medium, large",
        "source_id": "Integer(s), one or more comma-separated integers identifying map sources",
        "description": "A string to search for in the map unit description",
        "comments": "A string to search for in the map unit comments",
        "lith_type": "String, one or more comma-separated lithology types",
        "lith_class": "String, one or more comma-separated lithology classes",
        "lith_id": "Integer(s), one or more comma-separated integers identifying specific lithologies",
        "format": "Desired output format. Default is JSON",
        "sample": "Return a sample of data"
      },
      "output_formats": [
        "json",
        "csv"
      ],
      "examples": [
        "/api/v2/geologic_units/map/legend?source_id=1",
        "/api/v2/geologic_units/map/legend?description=banded%20iron",
        "/api/v2/geologic_units/map/legend?lith_type=carbonate"
      ],
      "fields": [
        "legend_id",
        "source_id",
        "scale",
        "map_unit_name",
        "strat_name",
        "unit_id",
        "age",
        "lith",
        "descrip",
        "comments",
        "b_age",
        "t_age",
        "b_interval",
        "t_interval",
        "strat_name_id",
        "lith_types",
        "lith_classes",
        "lith_id",
        "color",
        "area",
        "tiny_area",
        "small_area",
        "medium_area",
        "large_area"
      ]
    }
  },


  "/geologic_units/map/points": {
    "description": "Query point features from geologic maps",
    "visible": true,
    "parent": "geologic_units",
    "options": {
      "parameters": {
        "point_id": "One or more comma-separated valid point_ids",
        "point_type": "One or more comma-separated point_types",
        "certainty": "A string to search the certainty field for (fuzzy)",
        "comments": "A string to search the comments field for (fuzzy)",
        "source_id": "One or more comma-separated source_ids",
        "minlat": "A minimum latitude that represents the southwest corner of a bounding box (requires minlng, maxlat, and maxlng)",
        "minlng": "A minimum longitude that represents the southwest corner of a bounding box (requires minlat, maxlat, and maxlng)",
        "maxlat": "A maximum latitude that represents the northeast corner of a bounding box (requires minlat, minlng, and maxlng)",
        "maxlng": "A maximum longitude that represents the northeast corner of a bounding box (requires minlat, minlng, and maxlat)",
        "format": "Desired output format. Default is GeoJSON",
        "sample": "Return a sample of data"
      },
      "output_formats": [
        "geojson",
        "geojson_bare",
        "topojson",
        "topojson_bare",
        "csv"
      ],
      "examples": [
        "/api/v2/geologic_units/map/points?point_id=1,2,3",
        "/api/v2/geologic_units/map/points?point_type=joint",
        "/api/v2/geologic_units/map/points?minlng=-112.7672&minlat=36.0627&maxlng=-112.5390&maxlat=36.1872"
      ],
      "fields": [
        "point_id",
        "strike",
        "dip",
        "dip_dir",
        "point_type",
        "certainty",
        "comments",
        "source_id"
      ]
    }
  },

  "/geologic_units/burwell/nearby": {
    "description": "Stratigraphic names, lithologies, and time intervals near a coordinate in Burwell",
    "visible": false,
    "parent": "geologic_units",
    "options": {
      "parameters": {
        "lat": "A valid latitude in decimal degrees",
        "lng": "A valid longitude in decimal degrees",
        "format": "Desired output format"
      },
      "output_formats": [
        "json",
        "csv"
      ],
      "examples": [
        "/api/v2/geologic_units/burwell?lat=43&lng=-89.3"
      ],
      "fields": [

      ]
    }
  },

  "/geologic_units/map/nearby": {
    "description": "Stratigraphic names, lithologies, and time intervals near a coordinate in Macrostrat",
    "visible": false,
    "parent": "geologic_units",
    "options": {
      "parameters": {
        "lat": "A valid latitude in decimal degrees",
        "lng": "A valid longitude in decimal degrees",
        "format": "Desired output format"
      },
      "output_formats": [
        "json",
        "csv"
      ],
      "examples": [
        "/api/v2/geologic_units/map?lat=43&lng=-89.3"
      ],
      "fields": [

      ]
    }
  },

  "/carto": {
    "description": "Routes for creating geologic maps",
    "visible": true,
    "isParent": true
  },

  "/carto/small": {
    "description": "Returns Burwell polygons for mapping purposes",
    "parent": "carto",
    "visible": true,
    "options": {
      "parameters": {
        "sample": "Get a sample response",
        "lat": "A valid latitude in decimal degrees",
        "lng": "A valid longitude in decimal degrees",
        "shape": "A valid WKT geometry",
        "format": "Desired output format"
      },
      "output_formats": [
        "json",
        "csv",
        "geojson", "geojson_bare", "topojson", "topojson_bare"
      ],
      "examples": [
        ""
      ],
      "fields": [
        "map_id",
        "scale",
        "source_id",
        "name",
        "strat_name",
        "age",
        "lith",
        "descrip",
        "comments",
        "best_age_top",
        "best_age_bottom",
        "t_int",
        "b_int",
        "color"
      ]
    }
  },

  "/elevation": {
    "description": "Returns elevation in meters at a given coordinate from ETOPO1 and SRTM1",
    "visible": false,
    "options": {
      "parameters": {
        "lat": "A valid latitude",
        "lng": "A valid longitude",
        "format": "Desired output format"
      },
      "output_formats": [
        "json",
        "csv"
      ],
      "examples": [
        "api/elevation?lat=43&lng=-89"
      ],
      "fields": [
        "elevation"
      ]
    }
  },
  "/infer": {
    "description": "",
    "visible": false,
    "options": {
      "parameters": {
        "lat": "A valid latitude",
        "lng": "A valid longitude"
      },
      "output_formats": [
        "json"
      ],
      "examples": [
        "api/elevation?lat=43&lng=-89"
      ],
      "fields": [
        "elevation"
      ]
    }
  },
  "/grids": {
    "description": "Returns grids with the specified parameters",
    "visible": true,
    "isParent": true
  },
  "/grids/latitude": {
    "description": "Returns a grid given a longitude and latitude spacing",
    "parent": "grids",
    "visible": true,
    "options": {
      "parameters": {
        "lngSpacing": "divide bands of latitude by x degrees of longitude",
        "latSpacing": "the number of times a hemisphere should be cut",
        "format": "Desired output format"
      },
      "output_formats": [
        "geojson", "geojson_bare", "topojson", "topojson_bare"
      ],
      "examples": [
        "api/v2/grids/latitude?lngSpacing=5&latSpacing=12&format=geojson_bare"
      ],
      "fields": [
        "id",
        "area"
      ]
    }
  },
  "/grids/longitude": {
    "description": "Returns a grid given a latitude spacing and target cell size",
    "parent": "grids",
    "visible": true,
    "options": {
      "parameters": {
        "latSpacing": "the number of degrees between bands of latitude",
        "cellArea": "target cell area in km^2",
        "format": "Desired output format"
      },
      "output_formats": [
        "geojson", "geojson_bare", "topojson", "topojson_bare"
      ],
      "examples": [
        "api/v2/grids/longitude?latSpacing=5&cellArea=500000&format=geojson_bare"
      ],
      "fields": [
        "id",
        "area"
      ]
    }
  },

  "/grids/lithologies": {
    "description": "Returns a grid given a latitude and longitude spacing with burwell lithology info",
    "parent": "grids",
    "visible": true,
    "options": {
      "parameters": {
        "latSpacing": "the number of degrees between bands of latitude",
        "lngSpacing": "the number of degrees between bands of longitude",
        "originLat": "An optional origin latitude",
        "originLng": "An option origin longitude",
        "format": "Desired output format"
      },
      "output_formats": [
        "geojson", "geojson_bare", "topojson", "topojson_bare"
      ],
      "examples": [
        "api/v2/grids/longitude?latSpacing=5&cellArea=500000&format=geojson_bare"
      ],
      "fields": [
        "id",
        "area"
      ]
    }
  },


  "/places": {
    "description": "Returns places",
    "visible": false,
    "options": {
      "parameters": {
        "wof_id": "integer, the Who's on First ID",
        "name": "text, the place name",
        "name_like": "text, the place name (fuzzy match)",
        "placetype": "text, the type of the place (continent, country, region, county, or locality)",
        "childtype": "text, if provided, returns the specified childtype of the provided wof_id or name",
        "format": "Desired output format"
      },
      "output_formats": [
        "json","geojson", "geojson_bare", "topojson", "topojson_bare"
      ],
      "examples": [
        "/api/v2/places?wof_id=101732721",
        "api/v2/places?lng=-89.3843&lat=43.0748&placetype=region"
      ],
      "fields": [
        "wof_id",
        "name",
        "name_format",
        "placetype",
        "continent",
        "country",
        "region",
        "county",
        "other_names"
      ]
    }
  },

    "/hillshade": {
      "description": "Get a hillshade for a point at z12",
      "visible": false,
      "options": {
        "parameters": {
          "lat": "a valid latitude",
          "lng": "a valid longitude"
        },
        "output_formats": [
          "jpeg"
        ],
        "examples": [
        ],
        "fields": [

        ]
      }
    },

    "/boundaries": {
      "description": "Get geologic boundaries",
      "visible": false,
      "options": {
        "parameters": {
          "boundary_id": "A valid boundary id"
        },
        "output_formats": [
          "geojson"
        ],
        "examples": [
        ],
        "fields": [

        ]
      }
    },

    "/age_model": {
      "description": "Get all components of column age models; mostly unit_boundaries but can include other constraints",
      "visible": true,
      "options": {
        "parameters": {
          "col_id": "A valid col_id",
          "section_id": "A valid section_id"
        },
        "output_formats": [
          "json","csv"
        ],
        "examples": [
          "/age_models?section_id=1"
        ],
        "fields": [
          "boundary_id",
          "col_id",
          "section_id",
          "interval_id",
          "interval_name",
          "age_bottom",
          "age_top",
          "rel_position",
          "model_age",
          "boundary_status",
          "boundary_type",
          "unit_below",
          "unit_above"
        ]
      }
    },

    "/hex-summary": {
      "description": "Get corresponding data for hex grids",
      "visible": false,
      "options": {
        "parameters": {
          "zoom": "zoom level",
          "min_lng": "",
          "min_lat": "",
          "max_lng": "",
          "max_lat": ""
        },
        "output_formats": [
          "json"
        ],
        "examples": [
        ],
        "fields": [

        ]
      }
    },


  "/mobile": {
    "description": "Simplified data delivery, ideal for mobile applications",
    "visible": true,
    "isParent": true
  },
  "/mobile/point": {
    "description": "Get the largest scale geological map data available in Macrostrat/burwell for coordinates and relevant Macrostrat col_id (if any)",
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
    "description": "Get state-level geologic map unit description and Macrostrat units for a given location. A valid latitude and longitude or column ID and map unit ID are required.",
    "parent": "mobile",
    "visible": false,
    "options": {
      "parameters": {
        "lat": "A valid latitude",
        "lng": "A valid longitude",
        "col_id": "A valid column ID",
        "unit_id": "A valid map unit ID",
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

  "/mobile/macro_summary": {
    "description": "Summarize Macrostrat for a given location",
    "parent": "mobile",
    "visible": false,
    "options": {
      "parameters": {
        "lat": "numeric, a valid latitude",
        "lng": "numeric, a valid longitude"
      },
      "output_formats": [
        "json"
      ],
      "examples": [
        "/mobile/macro_summary?lat=43.0706192&lng=-89.406167"
      ],
      "fields": [
        "max_thick",
        "min_min_thick",
        "b_age",
        "t_age",
        "b_int_name",
        "t_int_name",
        "lith",
        "environ",
        "econs",
        "strat_names",
        "strat_name_ids",
        "c_int_name",
        "int_color",
        "lith_color"
      ]
    }
  },

  "/mobile/dashboard": {
    "description": "Summarize Macrostrat for a given location",
    "parent": "mobile",
    "visible": false,
    "options": {
      "parameters": {
        "lat": "numeric, a valid latitude",
        "lng": "numeric, a valid longitude"
      },
      "output_formats": [
        "json"
      ],
      "examples": [
        "/mobile/dashboard?lat=43.0706192&lng=-89.406167"
      ],
      "fields": [
        "max_thick",
        "min_min_thick",
        "b_age",
        "t_age",
        "b_int_name",
        "t_int_name",
        "lith",
        "environ",
        "econs",
        "strat_names",
        "strat_name_ids",
        "c_int_name",
        "int_color",
        "lith_color"
      ]
    }
  },

  "/mobile/map_query": {
    "description": "Query burwell (and Macrostrat) for a given location",
    "parent": "mobile",
    "visible": false,
    "options": {
      "parameters": {
        "lat": "numeric, a valid latitude",
        "lng": "numeric, a valid longitude",
        "z": "integer, a valid zoom level"
      },
      "output_formats": [
        "json"
      ],
      "examples": [
        "/mobile/map_query?lat=43.0706192&lng=-89.406167&z=10"
      ],
      "fields": [
      ]
    }
  },

  "/mobile/map_filter": {
    "description": "Filter burwell polygons",
    "parent": "mobile",
    "visible": false,
    "options": {
      "parameters": {
        "lith_id": "integer, one or more comma-separated lithology ids: matches strictly to lith field in map data",
        "lith_type": "string, one or more comma-separated lith_types: matches strictly to lith field in map data",
        "lith_class": "string, one or more comma-separated lith_classes: matches strictly to lith field in map data",
        "all_lith_id": "integer, one or more comma-separated lithology ids: matches any lith in any legend field",
        "all_lith_type": "string, one or more comma-separated lith_types: matches any lith_type in any legend field",
        "all_lith_class": "string, one or more comma-separated lith_classes: matches any lith_type in any legend field",
        "strat_name_id": "integer, one or more comma-separated strat_name_ids",
        "concept_id": "integer, one or more comma-separated strat_name concept_ids ids"
      },
      "output_formats": [
        "json"
      ],
      "examples": [

      ],
      "fields": [

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
    "col_group_id": "integer, the ID of the group to which the column belongs",
    "col_id": "integer, unique identifier for column",
    "col_name": "text, name of column",
    "columns": "integer, number of columns",
    "unit_id": "integer, unique identifier for unit",
    "section_id": "integer, unique identifier for section (package)",
    "sections": "int[], section_ids that belong to group",
    "pbdb_collections": "integer, count of PBDB collections in units/column",
    "pbdb_occurrences": "integer, count of PBDB occurrences in units/column",
    "pbdb_occs": "integer, count of PBDB occurrences in units in column",
    "project_id": "unique identifier for project, corresponds to general geographic region",
    "strat_name": "text, informal unit name",
    "strat_name_long": "text, the full formal name for a given strat_name",
    "strat_name_id": "integer, unique identifier for known stratigraphic name(s) (see /defs/strat_names)",
    "concept_id": "intger, unique identifier for the stratigraphic name concept, which groups variant strat_names for same entity",
    "strat_name_concept_id": "intger, unique identifier for the stratigraphic name concept, which groups variant strat_names for same entity",
    "name": "text, the name of the entity",
    "Mbr": "text, lithostratigraphic member",
    "Fm": "text, lithostratigraphic formation",
    "SubGp": "text, lithostratigraphic subgroup",
    "Gp": "text, lithostratigraphic group",
    "SGp": "text, lithostratigraphic supergroup",
    "era": "string, containing international chronostratigraphic period",
    "period": "string, containing international chronostratigraphic period",
    "max_thick": "number, maximum unit thickness in meters",
    "min_thick": "number, minimum unit thickess in meters (NB: some zero values may be equivalent in meaning to NULL)",
    "color": "text, recommended coloring for units based on dominant lithology",
    "u_color": "text, original color for unit",
    "mineral_color": "text, color description of mineral",
    "lustre": "text, description of mineral lustre",
    "crystal_form": "text, crystal form of mineral",
    "hardness_min": "decimal, minimum value for Moh's hardness scale",
    "hardness_max": "decimal, maximum value for Moh's hardness scale",
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
    "measurement_id": "integer, unique identifier for measurement",
    "sample_geo_unit": "text, description of unit supplying measurement",
    "measurement_type": "text, general measurement type",
    "measurement_class": "text, general measurement class",
    "measure_units": "text, units used in generating the measurement",
    "method": "text, method used to generate result",
    "measure_value": "number, reported value for measurement",
    "measure_error": "number, reported error associated with measure_value",
    "measure_n": "number, measurements used to compute measure_value, if greater than 1, typically also used in measure_error",
    "measure_position": "number, position of measurement in column, optionally section or unit; requires context of latter",
    "error_units": "text, units used in reported measure_error",
    "measure_type": "text, descriptor applying to nature of measure_value (e.g., point measurement, mean value for multiple point measurements)",
    "measure_phase": "text, material analyzed for measure_value (e.g., 'zircon' or 'whole rock')",
    "n": "integer, number of observations/measurements",
    "measuremeta_id": "integer, unique identifier for measuremeta (sample metadata)",
    "samp_lith": "text, lithological description of sample that produced measure_value",
    "samp_lith_id": "integer, unique identifier for lithology (see /defs/lithologies) in sample that produced measure_value",
    "samp_desc": "text, verbal description of sample used to generate",
    "samp_geo_unit": "text, geological unit yielding sample_measurement",
    "match_basis": "text, terse descriptor of what served to match measuremeta record to given macrostrat unit, if any",
    "samp_age": "text, geological time interval assigned to measurement",
    "unit_rel_pos": "number, position of measurement within a unit, usually proportional where 1=top, 0=bottom",
    "lith_max_thick": "number, thickness of specified lithology, based on proportion of unit(s)",
    "lith_min_thick": "number, thickness of specified lithology, based on proportion of unit(s)",
    "environ": "text, specific environment, see /defs/environments",
    "environ_type": "general environment type, /defs/environments",
    "environ_class": "text, general lithology class, /defs/environments",
    "outcrop": "text, describes where unit is exposed or not, values are  'outcrop', 'subsurface', or 'both'",
    "pbdb": "number of matching Paleobiology Database fossil collections",
    "units": "integer, unit_id matched to object",
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
    "ref": "text, name of reference",
    "cltn_id": "integer, Paleobiology Database collection ID",
    "cltn_name": "text, Paleobiology Database collection name",
    "col_area": "float, area in square kilometers of the Macrostrat column",
    "t_int_id": "integer, the ID of the chronostratigraphic interval containing the top boundary of the unit",
    "t_int_name": "text, the name of the chronostratigraphic interval containing the top boundary of the unit",
    "t_int_age": "float, the top age of the chronostratigraphic interval containing the top boundary of the unit",
    "units_above": "array of integers, the unit_ids of the units contacting the top of the unit",
    "b_int_id": "integer, the ID of the chronostratigraphic interval containing the bottom boundary of the unit",
    "b_int_name": "text, the name of the chronostratigraphic interval containing the bottom boundary of the unit",
    "b_int_age": "float, the bottom age of the chronostratigraphic interval containing the bottom boundary of the unit",
    "units_below": "array of integers, the unit_ids of the units contacting the bottom of the unit",
    "environ_id": "integer, the ID of the environment",
    "rank": "text, the stratigraphic rank of the unit",
    "lith_color": "text, the hex color associated with the lithology",
    "unit_com": "text, comments about the unit",
    "unitdesc": "text, description of the unit",
    "unit_name": "text, the name of the unit",
    "lithology": "array of strings, lithologies associated with the unit",
    "strat_names": "array of integer, strat_name_ids matched to the polygon or unit_link",
    "strat_unit": "text, the stratigraphic unit of the polygon",
    "gid": "integer, unique polygon ID of a map unit",
    "containing_interval": "text, the interval that includes the top and bottom ages of a unit",
    "unit_link": "text, the ID assigned to a given group of polygons that share common attributes",
    "macro_units": "array of integers, the unit_ids of Macrostrat units matched to the polygon or unit_link",
    "interval_color": "text, the hex color associated with the age of the unit",
    "lith_id": "integer, unique ID of the lithology",
    "measure_id": "integer, unique ID of the measurement",
    "group_col_id": "float, the original column ID assigned to the column (used in the original source)",
    "bed": "string, the strat_name of the bed",
    "bed_id": "integer, the strat_name_id of the bed",
    "mbr": "string, the strat_name of the member",
    "mbr_id": "integer, the strat_name_id of the member",
    "fm": "string, the strat_name of the formation",
    "fm_id": "integer, the strat_name_id of the formation",
    "gp": "string, the strat_name of the group",
    "gp_id": "integer, the strat_name_id of the group",
    "sgp": "string, the strat_name of the supergroup",
    "sgp_id": "integer, the strat_name_id of the supergroup",
    "lith_att_id": "integer, the unique ID of the lithology attribute",
    "lith_att": "string, the name of the lithology attribute",
    "att_type": "string, the lith_type of the lithology attribute",
    "pub_year": "integer, the year of publication",
    "author": "text, the author of the publication",
    "doi": "the digital object identifier of the publication",
    "url": "text, URL where additional information, the source or contributing publication can be found",
    "col_poly": "object, the GeoJSON representation of the column",
    "int_id": "integer, the unique interval ID",
    "int_type": "text, the temporal rank of the interval",
    "packages": "integer, total packages",
    "t_sections": "integer, total sections",
    "t_units": "integer, total units",
    "t_cols": "integer, total columns",
    "measure": "array, summary of types of measurements available",
    "max_min_thick": "integer, the maximum possible minimum thickness in meters",
    "min_min_thick": "integer, the minimum possible minimum thickness in meters",
    "source_id": "integer, unique Burwell source",
    "ref_title": "text, title of reference",
    "authors": "text, authors of source",
    "ref_year": "text, year of reference publication",
    "ref_source": "text, source of reference",
    "isbn_doi": "text, the reference ISBN or DOI",
    "scale": "text, the Burwell scale the source belongs to",
    "mineral_id": "integer, unqiue identifier for mineral",
    "mineral": "string, name of mineral",
    "mineral_type": "string, name of mineral group",
    "formula": "string, chemical formula of mineral",
    "formula_tags": "chemical formula of mineral with sub/superscript tags",
    "group": "string, defition group, less inclusive than type",
    "type": "string, definition type, less inclusive than class",
    "class": "string, definition class, more inclusive than type",
    "lat": "decimal, latitude in WGS84",
    "lng": "decimal, longigtude in WGS84",
    "structure_id": "integer, unique structure ID",
    "prop": "decimal, proportion",
    "genus_no": "integer, corresponds to the genus_no in Paleobiology Database",
    "taxon_no": "integer, corresponds to the taxn_no in Paleobiology Database",
    "point_id": "integer, unique ID of the point",
    "strike": "integer, point strike",
    "dip": "integer, point dip",
    "dip_dir": "integer, point dip direction",
    "point_type": "text, type of point",
    "certainty": "text, point location certainty",
    "grain_id": "Unique grain ID",
    "grain_symbol": "The grain symbol for display purposes",
    "grain_name": "The name of the grain",
    "grain_group": "The family of grains the grain belongs to",
    "soil_group": "The family of soils the grain belongs to",
    "classification": "The classification scheme the given grain belongs to",
    "min_size": "The minimum grainsize in millimeters",
    "max_size": "The maximum grainsize in millimeters",
    "descrip": "text, description of entity in plain text",
    "t_pos": "The position of unit top in ordering of units in section, optionally in units of m for some columns (e.g., eODP project)",
    "b_pos": "The position of unit bottom in ordering of units in section, optionally in units of m for some columns (e.g., eODP project)",
    "n_intervals": "integer, number of intervals in timescale.",
    "interval_name": "string, a valid interval name as defined in /defs/intervals",
    "age_bottom": "decimal, age of bottom of entity (interval_name or unit) in Ma",
    "age_top": "decimal, age of top of entity (interval_name or unit) in Ma",
    "best_age_bottom": "decimal, age of bottom of entity (map unit) in Ma; estimate is 'best' because it incorporates multiple age model sources",
    "best_age_top": "decimal, age of top of entity (map unit) in Ma; estimate is 'best' because it incorporates multiple age model sources",
    "map_unit_name": "name of map unit in original source, or modified original source",
    "legend_id": "integer, macrostrat internal identifier for map unit; one or more map_id values are assigned to a legend_id",
    "tiny_area": "number, area in km^2 of map polygons in tiny-scale topology",
    "small_area": "number, area in km^2 of map polygons in small-scale topology",
    "medium_area": "number, area in km^2 of map polygons in medium-scale topology",
    "large_area": "number, area in km^2 of map polygons in large-scale topology",
    "age": "string, chronostratigraphic bin assigned to object",
    "comments": "string, notes assigned to object"
  }
};
  module.exports = defs;
}());
