import { getUnitsData } from "./units";

import * as api from "./api";
import dbgeo from "dbgeo";
import * as larkin from "./larkin";
import _ from "underscore";
import gp from "geojson-precision";
import { acceptedFormats } from "./api";

export async function handleColumnRoute(req, res, next) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }
  try {
    const data = await getColumnData(req);
    const cfg = buildOutputConfig(req);
    return larkin.sendData(req, res, next, cfg, { data });
  } catch (error) {
    larkin.trace(error);
    return larkin.error(req, res, next, error.message);
  }
}

async function getColumnData(req) {
  // Get units data grouped by col_id
  const unitsResult = (await getUnitsData(req)) ?? [];

  // Group and process units data
  const cols = _.groupBy(unitsResult, (d) => d.col_id);
  const new_cols = processColumnsData(cols);

  // Query columns data
  const columnData = await queryColumnsData(req, new_cols);

  // Process and send response
  return await prepareColumnData(req, new_cols, columnData);
}

export function getColumnDataCompat(req, callback) {
  // Wrap the async logic in a promise but keep the outer handler sync
  (async () => {
    try {
      // Process and send response
      const res = await getColumnData(req);
      callback(null, res);
    } catch (error) {
      larkin.trace(error);
      return callback(error);
    }
  })();
}

async function prepareColumnData(req, unit_data, column_data) {
  let data = finalizeColumnsData(req, column_data, unit_data);
  if (req.query.format && acceptedFormats.geo[req.query.format]) {
    data = await buildGeoResult(req, data);
  }
  return data;
}

function processColumnsData(cols) {
  const new_cols = {};
  Object.keys(cols).forEach((col_id) => {
    new_cols[col_id] = {
      max_thick: _.reduce(
        cols[col_id].map((d) => d.max_thick),
        (a, b) => a + b,
        0,
      ),
      max_min_thick: _.reduce(
        cols[col_id].map((d) =>
          d.min_thick === 0 ? d.max_thick : d.min_thick,
        ),
        (a, b) => a + b,
        0,
      ),
      min_min_thick: _.reduce(
        cols[col_id].map((d) => d.min_thick),
        (a, b) => a + b,
        0,
      ),
      b_age: _.max(cols[col_id], (d) => d.b_age).b_age,
      t_age: _.min(cols[col_id], (d) => d.t_age).t_age,
      b_int_name: _.max(cols[col_id], (d) => d.b_age).b_int_name,
      t_int_name: _.min(cols[col_id], (d) => d.t_age).t_int_name,
      pbdb_collections: _.reduce(
        cols[col_id].map((d) => d.pbdb_collections),
        (a, b) => a + b,
        0,
      ),
      lith: larkin.summarizeAttribute(cols[col_id], "lith"),
      environ: larkin.summarizeAttribute(cols[col_id], "environ"),
      econ: larkin.summarizeAttribute(cols[col_id], "econ"),
      t_units: cols[col_id].length,
      t_sections: _.uniq(cols[col_id].map((d) => d.section_id)).length,
    };
  });
  return new_cols;
}

async function queryColumnsData(req, new_cols) {
  if (Object.keys(new_cols).length === 0) {
    return [];
  }

  const col_ids = Object.keys(new_cols).map((d) => parseInt(d));
  let params = { col_ids };

  const limit = "sample" in req.query ? " LIMIT 5" : "";
  let orderBy = "";
  let geo = "";

  // Base GROUP BY columns that are always needed
  const baseGroupBy = [
    "col_areas.col_id",
    "cols.id",
    "col_groups.col_group",
    "col_groups.id",
  ];
  let additionalGroupBy = [];

  // Handle status code
  if (req.query.status_code) {
    params["status_code"] = larkin.parseMultipleStrings(
      decodeURI(req.query.status_code),
    );
  } else {
    params["status_code"] = ["active"];
  }

  // Handle geometry - adds col_areas.col_area to GROUP BY
  const needsGeometry =
    req.query.format && api.acceptedFormats.geo[req.query.format];
  if (needsGeometry) {
    if (req.query.shape) {
      geo =
        ", ST_AsGeoJSON(ST_Intersection(col_areas.col_area, ST_MakeValid(:shape))) geojson";
      params["shape"] = req.query.shape;
    } else {
      geo = ", ST_AsGeoJSON(col_areas.col_area) geojson";
    }
    additionalGroupBy.push("col_areas.col_area");
  }

  // Handle ordering - also adds col_areas.col_area to GROUP BY if not already added
  if (req.query.lat && req.query.lng && req.query.adjacents) {
    orderBy =
      "ORDER BY ST_Distance(ST_SetSRID(col_areas.col_area, 4326), ST_SetSRID(ST_MakePoint(:lng, :lat), 4326))";
    params["lat"] = req.query.lat;
    params["lng"] = larkin.normalizeLng(req.query.lng);

    // Add col_areas.col_area to GROUP BY if not already added for geometry
    if (!needsGeometry) {
      additionalGroupBy.push("col_areas.col_area");
    }
  } else if (req.query.col_id && req.query.adjacents) {
    orderBy = `ORDER BY ST_Distance(
      ST_Centroid(col_areas.col_area),
      (SELECT ST_Centroid(col_area) FROM macrostrat.col_areas WHERE col_id = :col_id)
    )`;
    params["col_id"] = req.query.col_id;

    // Add col_areas.col_area to GROUP BY if not already added for geometry
    if (!needsGeometry) {
      additionalGroupBy.push("col_areas.col_area");
    }
  }

  // Assemble final GROUP BY clause
  const allGroupByColumns = [...baseGroupBy, ...additionalGroupBy];
  const groupByClause = `GROUP BY ${allGroupByColumns.join(", ")}`;

  const result = await larkin.queryPgAsync(
    "burwell",
    `
    SELECT
      cols.id AS col_id,
      col_name,
      col_group_long AS col_group,
      col_groups.id AS col_group_id,
      col AS group_col_id,
      cols.lat,
      cols.lng,
      round(cols.col_area::numeric, 1) AS col_area,
      cols.project_id,
      col_type,
      string_agg(col_refs.ref_id::varchar, '|') AS refs
      ${geo}
    FROM macrostrat.cols
    LEFT JOIN macrostrat.col_areas on col_areas.col_id = cols.id
    LEFT JOIN macrostrat.col_groups ON col_groups.id = cols.col_group_id
    LEFT JOIN macrostrat.col_refs ON cols.id = col_refs.col_id
    WHERE cols.status_code = ANY(:status_code)
      AND cols.id = ANY(:col_ids)
    ${groupByClause}
    ${orderBy}
    ${limit}
  `,
    params,
  );

  return result.rows;
}

function finalizeColumnsData(req, column_data, unit_data) {
  if (!column_data) return column_data;
  return column_data.map((init) => {
    let d = { ...init };
    if (typeof d.refs === "string" || d.refs instanceof String) {
      d.refs = larkin.jsonifyPipes(d.refs, "integers");
    }
    d.t_units = unit_data[d.col_id].t_units;
    d.t_sections = unit_data[d.col_id].t_sections;

    if (req.query.response === "long") {
      d = _.extend(d, unit_data[d.col_id]);

      if (req.query.format === "csv") {
        d.lith = larkin.pipifyAttrs(d.lith);
        d.environ = larkin.pipifyAttrs(d.environ);
        d.econ = larkin.pipifyAttrs(d.econ);
      }
    }
    return d;
  });
}

function buildOutputConfig(req) {
  let cfg = {
    format: acceptedFormats.standard[req.query.format]
      ? req.query.format
      : "json",
    compact: true,
    refs: "refs",
  };

  if (req.query.format && acceptedFormats.geo[req.query.format]) {
    cfg.bare = !!acceptedFormats.bare[req.query.format];
  }

  return cfg;
}

async function buildGeoResult(req, data) {
  const outputFormat = larkin.getOutputFormat(req.query.format);
  const output = await new Promise((resolve, reject) => {
    dbgeo.parse(
      data || [],
      {
        geometryColumn: "geojson",
        geometryType: "geojson",
        outputFormat,
      },
      (error, result) => {
        if (error) reject(new Error("An error was incurred during conversion"));
        else resolve(result);
      },
    );
  });

  return outputFormat === "geojson" ? gp(output, 4) : output;
}
