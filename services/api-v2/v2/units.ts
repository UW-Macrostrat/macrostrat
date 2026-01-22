var api = require("./api"),
  async = require("async"),
  dbgeo = require("dbgeo"),
  gp = require("geojson-precision"),
  larkin = require("./larkin");

import { buildProjectsFilter } from "./utils";

export function handleUnitsRoute(req, res, next, cb) {
  handleUnitsRouteAsync(req, res, next, cb).catch((error) => {
    larkin.trace(error);
    if (cb) {
      cb(error);
    } else {
      return larkin.error(req, res, next, error.message);
    }
  });
}

export async function getUnitsData(req) {
  let params = {};

  // First determine age range component of query, if any.
  const data = await determineAgeRange(req, params);

  // Build the main query
  return await buildAndExecuteMainQuery(req, data, params, () => {});
}

async function handleUnitsRouteAsync(req, res, next, cb) {
  // If no parameters, send the route definition
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }

  const result = getUnitsData(req);

  if (cb) {
    cb(null, result);
  } else {
    return larkin.sendData(
      req,
      res,
      next,
      {
        format: api.acceptedFormats.standard[req.query.format]
          ? req.query.format
          : "json",
        bare: api.acceptedFormats.bare[req.query.format] ? true : false,
        refs: req.query.response === "long" ? "refs" : false,
      },
      {
        data: result,
      },
    );
  }
}

async function determineAgeRange(req, params) {
  if (req.query.interval_name) {
    params["interval_name"] = req.query.interval_name;
    const sql = `SELECT age_bottom, age_top, interval_name FROM macrostrat.intervals WHERE interval_name = :interval_name LIMIT 1`;
    const result = await larkin.queryPgAsync("burwell", sql, params);

    if (result.rowCount == 0) {
      throw new Error("No results found");
    }

    return {
      interval_name: result.rows[0].interval_name,
      age_bottom: result.rows[0].age_bottom,
      age_top: result.rows[0].age_top,
    };
  }

  if (req.query.int_id) {
    const sql =
      "SELECT age_bottom, age_top, interval_name FROM macrostrat.intervals WHERE id = :int_id LIMIT 1";
    params["int_id"] = req.query.int_id;
    const result = await larkin.queryPgAsync("burwell", sql, params);

    if (result.rowCount == 0) {
      return {
        interval_name: "none",
        age_bottom: 0,
        age_top: 9999999,
      };
    }

    return {
      interval_name: result.rows[0].interval_name,
      age_bottom: result.rows[0].age_bottom,
      age_top: result.rows[0].age_top,
    };
  }

  if (req.query.age) {
    return {
      interval_name: "none",
      age_bottom: req.query.age,
      age_top: req.query.age,
    };
  }

  if (req.query.age_top && req.query.age_bottom) {
    return {
      interval_name: "none",
      age_bottom: req.query.age_bottom,
      age_top: req.query.age_top,
    };
  }

  if (req.query.shape) {
    const result = await larkin.queryPgAsync(
      "burwell",
      `SELECT id FROM macrostrat.cols WHERE ST_Intersects(poly_geom, ST_GeomFromText($1, 4326))`,
      [req.query.shape],
    );

    return {
      interval_name: "none",
      age_bottom: 99999,
      age_top: 0,
      col_ids: result.rows.map((d) => d.id),
    };
  }

  if (req.query.lat && req.query.lng) {
    const sql =
      req.query.adjacents === "true"
        ? "WITH containing_geom AS (SELECT poly_geom FROM macrostrat.cols WHERE ST_Contains(poly_geom, ST_GeomFromText(:point, 4326))) SELECT id FROM macrostrat.cols WHERE ST_Intersects((SELECT * FROM containing_geom), poly_geom) ORDER BY ST_Distance(ST_Centroid(poly_geom), ST_GeomFromText($1, 4326))"
        : "SELECT id FROM macrostrat.cols WHERE ST_Contains(poly_geom, st_setsrid(ST_GeomFromText(:point), 4326)) ORDER BY ST_Distance(ST_Centroid(poly_geom), ST_GeomFromText(:point, 4326))";

    params["point"] =
      "POINT(" + larkin.normalizeLng(req.query.lng) + " " + req.query.lat + ")";

    const response = await larkin.queryPgAsync("burwell", sql, params);
    return {
      interval_name: "none",
      age_bottom: 99999,
      age_top: 0,
      col_ids: response.rows.map((d) => d.id),
    };
  }

  if (req.query.col_id && req.query.adjacents) {
    const col_ids = larkin.parseMultipleIds(req.query.col_id);
    const placeholders = col_ids.map((d, i) => "$" + (i + 1));

    let sql =
      "WITH containing_geom AS (SELECT poly_geom FROM macrostrat.cols WHERE id IN (" +
      placeholders.join(",") +
      ")) SELECT id FROM macrostrat.cols WHERE ST_Intersects((SELECT * FROM containing_geom), poly_geom)";

    if (col_ids.length === 1) {
      sql +=
        " ORDER BY ST_Distance(ST_Centroid(poly_geom), (SELECT * FROM containing_geom))";
    }

    const response = await larkin.queryPgAsync("burwell", sql, col_ids);
    return {
      interval_name: "none",
      age_bottom: 99999,
      age_top: 0,
      col_ids: response.rows.map((d) => d.id),
    };
  }

  if (req.query.col_group_id) {
    const result = await larkin.queryPgAsync(
      "burwell",
      "SELECT id FROM macrostrat.cols WHERE col_group_id = ANY(:col_group_ids)",
      { col_group_ids: larkin.parseMultipleIds(req.query.col_group_id) },
    );

    return {
      interval_name: "none",
      age_bottom: 99999,
      age_top: 0,
      col_ids: result.rows.map((d) => d.id),
    };
  }

  if (req.query.strat_name) {
    const result = await larkin.queryPgAsync(
      "burwell",
      "SELECT strat_name_id FROM macrostrat.lookup_strat_names WHERE strat_name ILIKE :strat_name",
      { strat_name: "%" + req.query.strat_name + "%" },
    );

    if (result.rows.length === 0) {
      throw new Error("No results found");
    }

    return {
      interval_name: "none",
      age_bottom: 99999,
      age_top: 0,
      strat_ids: result.rows.map((d) => d.strat_name_id),
    };
  }

  if (req.query.strat_name_concept_id) {
    const result = await larkin.queryPgAsync(
      "burwell",
      "SELECT id FROM macrostrat.strat_names WHERE concept_id = ANY(:strat_name_concept_ids)",
      {
        strat_name_concept_ids: larkin.parseMultipleIds(
          req.query.strat_name_concept_id,
        ),
      },
    );

    if (result.rows.length === 0) {
      return {
        interval_name: "none",
        age_bottom: 99999,
        age_top: 0,
        strat_ids: [null],
      };
    }

    return {
      interval_name: "none",
      age_bottom: 99999,
      age_top: 0,
      strat_ids: result.rows.map((d) => d.id),
    };
  }

  if (req.query.strat_name_id) {
    return {
      interval_name: "none",
      age_bottom: 99999,
      age_top: 0,
      strat_ids: larkin.parseMultipleIds(req.query.strat_name_id),
    };
  }

  if (
    req.query.unit_id ||
    req.query.section_id ||
    req.query.col_id ||
    req.query.lith ||
    req.query.lith_id ||
    req.query.lith_class ||
    req.query.lith_type ||
    req.query.lith_group ||
    req.query.environ ||
    req.query.environ_id ||
    req.query.environ_class ||
    req.query.environ_type ||
    req.query.project_id ||
    "sample" in req.query ||
    "all" in req.query ||
    req.query.econ_id ||
    req.query.econ ||
    req.query.econ_type ||
    req.query.econ_class ||
    req.query.cltn_id ||
    req.query.lith_att_id ||
    req.query.lith_att ||
    req.query.lith_att_type ||
    req.query.col_type ||
    req.query.status_code
  ) {
    return {
      interval_name: "none",
      age_bottom: 99999,
      age_top: 0,
    };
  }

  throw new Error("Invalid parameters passed");
}

async function buildAndExecuteMainQuery(req, data, params, cb) {
  let where = "";
  const limit = "sample" in req.query ? (cb ? " LIMIT 15 " : " LIMIT 5") : "";
  const orderby = [];

  larkin.trace(data);

  // Build WHERE clauses
  if (req.query.status_code) {
    where += "cols.status_code = ANY(:status_code)";
    params["status_code"] = larkin.parseMultipleStrings(
      decodeURI(req.query.status_code),
    );
  } else {
    where += "cols.status_code = 'active'";
  }

  // Add lith filters
  if (
    req.query.lith ||
    req.query.lith_class ||
    req.query.lith_type ||
    req.query.lith_id ||
    req.query.lith_group
  ) {
    where +=
      " AND units.id = ANY(SELECT unit_liths.unit_id FROM macrostrat.unit_liths JOIN macrostrat.liths ON lith_id = liths.id WHERE ";
    const lithWhere = [];

    if (req.query.lith) {
      lithWhere.push("lith = ANY(:lith)");
      params["lith"] = larkin.parseMultipleStrings(req.query.lith);
    }
    if (req.query.lith_class) {
      lithWhere.push("lith_class = ANY(:lith_class)");
      params["lith_class"] = larkin.parseMultipleStrings(req.query.lith_class);
    }
    if (req.query.lith_type) {
      lithWhere.push("lith_type = ANY(:lith_type)");
      params["lith_type"] = larkin.parseMultipleStrings(req.query.lith_type);
    }
    if (req.query.lith_group) {
      lithWhere.push("lith_group = ANY(:lith_group)");
      params["lith_group"] = larkin.parseMultipleStrings(req.query.lith_group);
    }
    if (req.query.lith_id) {
      lithWhere.push("liths.id = ANY(:lith_id)");
      params["lith_id"] = larkin.parseMultipleIds(req.query.lith_id);
    }

    where += lithWhere.join(" OR ") + ")";
  }

  // Add lith_att filters
  if (req.query.lith_att_id || req.query.lith_att || req.query.lith_att_type) {
    let lithAttField;
    if (req.query.lith_att_id) {
      lithAttField = "unit_liths_atts.lith_att_id";
      params["lith_att"] = larkin.parseMultipleIds(req.query.lith_att_id);
    } else if (req.query.lith_att) {
      lithAttField = "lith_atts.lith_att";
      params["lith_att"] = larkin.parseMultipleStrings(req.query.lith_att);
    } else if (req.query.lith_att_type) {
      lithAttField = "lith_atts.att_type";
      params["lith_att"] = larkin.parseMultipleStrings(req.query.lith_att_type);
    }

    where += ` AND units.id = ANY(
      SELECT unit_liths.unit_id
      FROM macrostrat.unit_liths
      JOIN macrostrat.liths ON lith_id = liths.id
      JOIN macrostrat.unit_liths_atts ON unit_liths_atts.unit_lith_id = unit_liths.id
      JOIN macrostrat.lith_atts ON unit_liths_atts.lith_att_id = lith_atts.id
      WHERE ${lithAttField} = ANY(:lith_att)
    )`;
  }

  // Add age filters - Fixed column reference
  if (data.age_bottom !== 99999) {
    where +=
      " AND lookup_units.b_age > :age_top AND lookup_units.t_age < :age_bottom";
    params["age_top"] = data.age_top;
    params["age_bottom"] = data.age_bottom;
  }

  // Add remaining filters...
  if (req.query.unit_id) {
    where += " AND units.id = ANY(:unit_id)";
    params["unit_id"] = larkin.parseMultipleIds(req.query.unit_id);
    orderby.push(" units.id ");
  }

  if (req.query.section_id) {
    where += " AND units_sections.section_id = ANY(:section_id)";
    params["section_id"] = larkin.parseMultipleIds(req.query.section_id);
  }

  if ("col_ids" in data) {
    where += " AND units_sections.col_id = ANY(:col_id)";
    if (!data.col_ids.length) {
      data.col_ids = [""];
    }
    params["col_id"] = data.col_ids;
  } else if (req.query.col_id) {
    where += " AND units_sections.col_id = ANY(:col_id)";
    params["col_id"] = larkin.parseMultipleIds(req.query.col_id);
  }

  if (data.strat_ids) {
    where +=
      " AND (lookup_strat_names.bed_id = ANY(:strat_ids) OR lookup_strat_names.mbr_id = ANY(:strat_ids) OR lookup_strat_names.fm_id = ANY(:strat_ids) OR lookup_strat_names.gp_id = ANY(:strat_ids) OR lookup_strat_names.sgp_id = ANY(:strat_ids))";
    params["strat_ids"] = data.strat_ids;
  }

  const [whereClauses, projectParams] = buildProjectsFilter(
    req,
    "lookup_units.project_id",
  );
  if (whereClauses.length > 0) {
    where += " AND " + whereClauses.join(" AND ");
    Object.assign(params, projectParams);
  }

  // Add environ filters
  if (
    req.query.environ_id ||
    req.query.environ ||
    req.query.environ_class ||
    req.query.environ_type
  ) {
    where +=
      " AND units.id = ANY(SELECT unit_environs.unit_id FROM macrostrat.unit_environs JOIN macrostrat.environs on environ_id=environs.id WHERE ";
    const environWhere = [];

    if (req.query.environ) {
      environWhere.push("environ = ANY(:environ)");
      params["environ"] = larkin.parseMultipleStrings(req.query.environ);
    }
    if (req.query.environ_class) {
      environWhere.push("environ_class = ANY(:environ_class)");
      params["environ_class"] = larkin.parseMultipleStrings(
        req.query.environ_class,
      );
    }
    if (req.query.environ_type) {
      environWhere.push("environ_type = ANY(:environ_type)");
      params["environ_type"] = larkin.parseMultipleStrings(
        req.query.environ_type,
      );
    }
    if (req.query.environ_id) {
      environWhere.push("environs.id = ANY(:environ_id)");
      params["environ_id"] = larkin.parseMultipleIds(req.query.environ_id);
    }

    where += environWhere.join(" OR ") + ")";
  }

  // Add econ filters
  if (
    req.query.econ_id ||
    req.query.econ ||
    req.query.econ_type ||
    req.query.econ_class
  ) {
    let econ_field;
    if (req.query.econ_id) {
      params["econ"] = larkin.parseMultipleIds(req.query.econ_id);
      econ_field = "econs.id";
    } else if (req.query.econ) {
      params["econ"] = larkin.parseMultipleStrings(req.query.econ);
      econ_field = "econs.econ";
    } else if (req.query.econ_type) {
      params["econ"] = larkin.parseMultipleStrings(req.query.econ_type);
      econ_field = "econs.econ_type";
    } else if (req.query.econ_class) {
      params["econ"] = larkin.parseMultipleStrings(req.query.econ_class);
      econ_field = "econs.econ_class";
    }

    where += ` AND units.id = ANY(SELECT unit_econs.unit_id
      FROM macrostrat.unit_econs
      JOIN macrostrat.econs on econ_id=econs.id
      WHERE ${econ_field} = ANY(:econ))`;
  }

  if (req.query.cltn_id) {
    where +=
      " AND units.id = ANY(SELECT unit_id FROM macrostrat.pbdb_matches WHERE collection_no = ANY(:cltn_ids))";
    params["cltn_ids"] = larkin.parseMultipleIds(req.query.cltn_id);
  }

  if (req.query.col_type) {
    where += " AND cols.col_type = ANY(:col_type)";
    params["col_type"] = larkin.parseMultipleStrings(req.query.col_type);
  }

  if ("sample" in req.query) {
    where +=
      " AND units_sections.col_id = ANY(ARRAY[92, 488, 463, 289, 430, 481, 261, 534, 369, 798, 771, 1675])";
  }

  const measureField =
    "summarize_measures" in req.query
      ? "lookup_unit_attrs_api.measure_long"
      : "lookup_unit_attrs_api.measure_short";

  let columnList = `
    DISTINCT ON (units.id)
    units.id AS unit_id,
    units_sections.section_id AS section_id,
    units_sections.col_id AS col_id,
    cols.project_id,
    cols.col_area,
    units.strat_name AS unit_name,
    unit_strat_names.strat_name_id,
    COALESCE(mbr_name, '') AS "Mbr",
    COALESCE(fm_name, '') AS "Fm",
    COALESCE(gp_name, '') AS "Gp",
    COALESCE(sgp_name, '') AS "SGp",
    lookup_units.t_age::float,
    lookup_units.b_age::float,
    units.max_thick::float,
    units.min_thick::float,
    units.outcrop,
    lookup_units.pbdb_collections::integer,
    lookup_units.pbdb_occurrences::integer`;

  if (req.query.response === "long" || cb) {
    const colRefsSubquery = `SELECT string_agg(col_refs.ref_id::text, '|') FROM macrostrat.col_refs WHERE col_refs.col_id = cols.id`;

    columnList += `,
      lookup_unit_attrs_api.lith,
      lookup_unit_attrs_api.environ,
      lookup_unit_attrs_api.econ,
      ${measureField} AS measure,
      COALESCE(notes, '') AS notes,
      lookup_units.color,
      lookup_units.text_color,
      lookup_units.t_int AS t_int_id,
      lookup_units.t_int_name,
      lookup_units.t_int_age::float,
      lookup_units.t_prop::float,
      lookup_units.units_above,
      lookup_units.b_int AS b_int_id,
      lookup_units.b_int_name,
      lookup_units.b_int_age::float,
      lookup_units.b_prop::float,
      lookup_units.units_below,
      lookup_strat_names.rank_name AS strat_name_long,
      (${colRefsSubquery}) AS refs`;

    if ("show_position" in req.query) {
      columnList += ", position_top AS t_pos, position_bottom AS b_pos";
    }
  }

  if (
    (req.query.format && api.acceptedFormats.geo[req.query.format]) ||
    req.query.response === "long"
  ) {
    columnList +=
      ", lookup_units.clat::float, lookup_units.clng::float, lookup_units.t_plat::float, lookup_units.t_plng::float, lookup_units.b_plat::float, lookup_units.b_plng::float";
  }

  const sql = `
    WITH orig_query AS (SELECT ${columnList}
    FROM macrostrat.units
    LEFT JOIN macrostrat.lookup_unit_attrs_api ON lookup_unit_attrs_api.unit_id = units.id
    LEFT JOIN macrostrat.lookup_units ON units.id = lookup_units.unit_id
    LEFT JOIN macrostrat.unit_strat_names ON unit_strat_names.unit_id=units.id
    LEFT JOIN macrostrat.units_sections ON units.id = units_sections.unit_id
    LEFT JOIN macrostrat.cols ON units_sections.col_id = cols.id
    LEFT JOIN macrostrat.col_refs ON cols.id = col_refs.col_id
    LEFT JOIN macrostrat.lookup_strat_names ON lookup_strat_names.strat_name_id=unit_strat_names.strat_name_id
    LEFT JOIN macrostrat.unit_notes ON unit_notes.unit_id=units.id
    WHERE ${where}
    ${orderby.length > 0 ? `ORDER BY ${orderby.join(", ")} ASC` : ""})
    SELECT * FROM orig_query
    ORDER BY t_age ASC
    ${limit}`;

  const result = await larkin.queryPgAsync("burwell", sql, params);

  // Process results
  if (req.query.response === "long" || cb) {
    for (let i = 0; i < result.rows.length; i++) {
      result.rows[i].lith = JSON.parse(result.rows[i].lith) || [];
      result.rows[i].environ = JSON.parse(result.rows[i].environ) || [];
      result.rows[i].econ = JSON.parse(result.rows[i].econ) || [];
      result.rows[i].measure = JSON.parse(result.rows[i].measure) || [];
      result.rows[i].units_above = larkin.jsonifyPipes(
        result.rows[i].units_above,
        "integers",
      );
      result.rows[i].units_below = larkin.jsonifyPipes(
        result.rows[i].units_below,
        "integers",
      );
      result.rows[i].refs = larkin.jsonifyPipes(
        result.rows[i].refs,
        "integers",
      );
    }
  }

  if (req.query.format === "csv" && req.query.response === "long" && !cb) {
    for (let i = 0; i < result.rows.length; i++) {
      result.rows[i].units_above = result.rows[i].units_above.join(",");
      result.rows[i].units_below = result.rows[i].units_below.join(",");
      result.rows[i].lith = larkin.pipifyAttrs(result.rows[i].lith);
      result.rows[i].environ = larkin.pipifyAttrs(result.rows[i].environ);
      result.rows[i].econ = larkin.pipifyAttrs(result.rows[i].econ);
      result.rows[i].refs = result.rows[i].refs.join("|");
    }
  }

  if (req.query.format && api.acceptedFormats.geo[req.query.format] && !cb) {
    const geomAge =
      req.query.geom_age && req.query.geom_age === "top"
        ? ["t_plng", "t_plat"]
        : req.query.geom_age === "bottom"
          ? ["b_plng", "b_plat"]
          : ["clng", "clat"];

    return new Promise((resolve, reject) => {
      dbgeo.parse(
        result.rows,
        {
          geometryType: "ll",
          geometryColumn: geomAge,
          outputFormat: larkin.getOutputFormat(req.query.format),
        },
        function (error, output) {
          if (error) {
            reject(new Error("An error was incurred during conversion"));
          } else {
            if (larkin.getOutputFormat(req.query.format) === "geojson") {
              output = gp(output, 4);
            }
            resolve(output);
          }
        },
      );
    });
  }

  return result.rows;
}
