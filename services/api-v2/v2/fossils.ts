import { getUnitsData } from "./units";

var api = require("./api"),
  dbgeo = require("dbgeo"),
  larkin = require("./larkin");

import { buildProjectsFilter } from "./utils";

export async function handleFossilsRoute(req, res, next) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }

  try {
    const geo =
      req.query.format && api.acceptedFormats.geo[req.query.format]
        ? true
        : false;

    // First step: determine age range and unit constraints
    const data = await determineAgeRangeAndUnits(req);

    if (data === null) {
      return larkin.sendData(
        req,
        res,
        next,
        {
          format: api.acceptedFormats.standard[req.query.format]
            ? req.query.format
            : "json",
          refs: "refs",
        },
        {
          data: [],
        },
      );
    }

    // Second step: build and execute the main query
    const results = await buildAndExecuteFossilsQuery(req, data, geo);

    // Handle geo formatting if needed
    if (geo) {
      const geoResult = await new Promise((resolve, reject) => {
        dbgeo.parse(
          results.rows,
          {
            outputFormat: larkin.getOutputFormat(req.query.format),
            geometryColumn: "geometry",
            geometryType: "wkt",
          },
          function (error, result) {
            if (error) {
              reject(new Error("Something went wrong"));
            } else {
              resolve(result);
            }
          },
        );
      });

      return larkin.sendData(
        req,
        res,
        next,
        {
          format: api.acceptedFormats.standard[req.query.format]
            ? req.query.format
            : "json",
          bare: api.acceptedFormats.bare[req.query.format] ? true : false,
          refs: "refs",
        },
        {
          data: geoResult,
        },
      );
    } else {
      return larkin.sendData(
        req,
        res,
        next,
        {
          format: api.acceptedFormats.standard[req.query.format]
            ? req.query.format
            : "json",
          refs: "refs",
        },
        {
          data: results.rows,
        },
      );
    }
  } catch (error) {
    larkin.trace(error);
    return larkin.error(req, res, next, error.message);
  }
}

async function determineAgeRangeAndUnits(req) {
  if (req.query.age_top && req.query.age_bottom) {
    return {
      interval_name: "Unknown",
      age_bottom: req.query.age_bottom,
      age_top: req.query.age_top,
    };
  }

  if (req.query.age) {
    return {
      interval_name: "Unknown",
      age_bottom: req.query.age,
      age_top: req.query.age,
    };
  }

  if (
    req.query.unit_id ||
    req.query.col_id ||
    req.query.col_group_id ||
    req.query.strat_name_id ||
    req.query.strat_name_concept_id ||
    req.query.project_id ||
    "sample" in req.query
  ) {
    return {
      interval_name: "Unknown",
      age_bottom: null,
      age_top: null,
    };
  }

  if (
    req.query.interval_name ||
    req.query.int_id ||
    req.query.lith_id ||
    req.query.lith ||
    req.query.lith_type ||
    req.query.lith_class ||
    req.query.environ_id ||
    req.query.environ ||
    req.query.environ_type ||
    req.query.environ_class ||
    req.query.econ_id ||
    req.query.econ ||
    req.query.econ_type ||
    req.query.econ_class
  ) {
    const result = await getUnitsData(req);

    if (!result || !result.length) {
      return null;
    }

    req.query.unit_id = result
      .map(function (d) {
        return d.unit_id;
      })
      .join(",");

    return {
      interval_name: "Unknown",
      age_bottom: null,
      age_top: null,
    };
  }

  throw new Error("Invalid parameters");
}

async function buildAndExecuteFossilsQuery(req, data, geo) {
  let where = "";
  const limit = "sample" in req.query ? " LIMIT 5" : "";
  const params = {};

  if (data.age_bottom) {
    where +=
      " AND lookup_unit_intervals.b_age > :age_top AND lookup_unit_intervals.t_age < :age_bottom";
    params["age_top"] = data.age_top;
    params["age_bottom"] = data.age_bottom;
  }

  if (req.query.unit_id) {
    where += " AND pbdb_matches.unit_id = ANY(:unit_id)";
    params["unit_id"] = larkin.parseMultipleIds(req.query.unit_id);
  } else if (req.query.col_id) {
    where += " AND units_sections.col_id = ANY(:col_id)";
    params["col_id"] = larkin.parseMultipleIds(req.query.col_id);
  }

  if (req.query.strat_name_id) {
    where +=
      " AND (lookup_strat_names.bed_id = ANY(:strat_name_ids) OR lookup_strat_names.mbr_id = ANY(:strat_name_ids) OR lookup_strat_names.fm_id = ANY(:strat_name_ids) OR lookup_strat_names.gp_id = ANY(:strat_name_ids) OR lookup_strat_names.sgp_id = ANY(:strat_name_ids)) ";
    params["strat_name_ids"] = larkin.parseMultipleIds(req.query.strat_name_id);
  }

  if (req.query.strat_name_concept_id) {
    where +=
      " AND lookup_strat_names.strat_name_id = ANY(SELECT strat_name_id FROM lookup_strat_names WHERE concept_id = ANY(:concept_id))";
    params["concept_id"] = larkin.parseMultipleIds(
      req.query.strat_name_concept_id,
    );
  }

  if (req.query.col_group_id) {
    where += " AND col_group_id = ANY(:col_group_ids)";
    params["col_group_ids"] = larkin.parseMultipleIds(req.query.col_group_id);
  }

  const [projectWhereClauses, projectParams] = buildProjectsFilter(
    req,
    "cols.project_id",
  );
  where += projectWhereClauses.length
    ? " AND " + projectWhereClauses.join(" AND ")
    : "";
  Object.assign(params, projectParams);

  const sql = `
    SELECT pbdb_matches.collection_no AS cltn_id, collection_name AS cltn_name, lookup_unit_intervals.t_age::float, lookup_unit_intervals.b_age::float,
    occs as pbdb_occs, pbdb_matches.unit_id, cols.id as col_id, CONCAT(pbdb_matches.ref_id, '|') AS refs
    ${geo ? ", ST_AsText(pbdb_matches.coordinate) AS geometry" : ""}
    , lookup_strat_names.concept_id AS strat_name_concept_id
    FROM macrostrat.pbdb_matches
    JOIN macrostrat.units ON pbdb_matches.unit_id = units.id
    JOIN macrostrat.units_sections ON units_sections.unit_id = units.id
    JOIN macrostrat.cols ON cols.id = units_sections.col_id
    JOIN macrostrat.lookup_unit_intervals ON units_sections.unit_id=lookup_unit_intervals.unit_id
    LEFT JOIN macrostrat.unit_strat_names ON unit_strat_names.unit_id = units.id
    LEFT JOIN macrostrat.lookup_strat_names ON lookup_strat_names.strat_name_id=unit_strat_names.strat_name_id
    WHERE macrostrat.pbdb_matches.release_date < now() AND
    macrostrat.cols.status_code = 'active' ${where}
    GROUP BY pbdb_matches.collection_no, pbdb_matches.collection_name, lookup_unit_intervals.t_age, lookup_unit_intervals.b_age, pbdb_matches.occs, pbdb_matches.unit_id, cols.id, pbdb_matches.ref_id, pbdb_matches.coordinate, lookup_strat_names.concept_id
    ${limit}`;

  const result = await larkin.queryPgAsync("burwell", sql, params);

  result.rows = result.rows.map(function (d) {
    // Hardcoding genus_no and taxon_no as mentioned in original comments
    d.genus_no = [];
    d.taxon_no = "";
    d.refs = larkin.jsonifyPipes(d.refs, "integers");

    if (req.query.format && req.query.format === "csv") {
      d.refs = d.refs.join("|");
      d.genus_no = [];
      d.taxon_no = "";
    }

    return {
      cltn_id: d.cltn_id,
      cltn_name: d.cltn_name,
      t_age: d.t_age,
      b_age: d.b_age,
      pbdb_occs: d.pbdb_occs,
      genus_no: d.genus_no,
      taxon_no: d.taxon_no,
      unit_id: d.unit_id,
      col_id: d.col_id,
      refs: d.refs,
      strat_name_concept_id: d.strat_name_concept_id,
      ...(geo && d.geometry ? { geometry: d.geometry } : {}),
    };
  });

  return result;
}
