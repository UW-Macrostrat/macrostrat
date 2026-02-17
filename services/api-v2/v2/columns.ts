import { getColumnFilters, getUnitsData } from "./units";

import dbgeo from "dbgeo";
import * as larkin from "./larkin";
import _ from "underscore";
import gp from "geojson-precision";
import { acceptedFormats } from "./api";
import { sharedUnitFilters } from "./defs";
import { buildSQLQuery } from "./utils";

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
  // New: a "fast path" where we can skip units processing if only column IDs are requested
  //if (isUnitFilteringRequired(req))

  let unitGroups = null;
  // Get units data grouped by col_id
  if (isUnitFilteringRequired(req)) {
    const unitsResult = (await getUnitsData(req)) ?? [];

    // Group and process units data
    const unitMap = _.groupBy(unitsResult, (d) => d.col_id);
    unitGroups = synthesizeColumnDataFromGroupedUnits(unitMap);
  }

  // Query columns data
  const columnData = await queryColumnsData(req, unitGroups);

  // Process and send response
  return await prepareColumnData(req, columnData, unitGroups);
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

export function isUnitFilteringRequired(req) {
  const columnFilters = [
    "col_id",
    "col_type",
    "project_id",
    "status_code",
    "adjacents",
    "lat",
    "lng",
    "response",
    "format",
  ];

  for (const param in req.query) {
    if (!columnFilters.includes(param) && param in sharedUnitFilters) {
      return true;
    }
  }
  if (req.query.response === "long") {
    // If we want long response, we need unit data
    return true;
  }

  return false;
}

type ColumnData = {
  [key: string]: any;
  col_id: number;
}[];

type UnitDataMap = {
  [col_id: number]: any;
};

async function prepareColumnData(
  req,
  column_data: ColumnData,
  unit_data: UnitDataMap | null,
) {
  let data = finalizeColumnsData(req, column_data, unit_data);
  if (req.query.format && acceptedFormats.geo[req.query.format]) {
    data = await buildGeoResult(req, data);
  }
  return data;
}

function synthesizeColumnDataFromGroupedUnits(cols) {
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

async function queryColumnsData(req, new_cols: UnitDataMap | null) {
  let { orderByClauses, whereClauses, groupByClauses, params } =
    getColumnFilters(req, "col_areas");

  if (new_cols !== null && Object.keys(new_cols).length > 0) {
    const col_ids = Object.keys(new_cols).map((d) => parseInt(d));
    whereClauses.push("cols.id = ANY(:col_ids_from_units::integer[])");
    params = { ...params, col_ids_from_units: col_ids };
  }

  const limit = "sample" in req.query ? 5 : null;
  let geo = "";

  // Base GROUP BY columns that are always needed
  groupByClauses.push(
    "col_areas.col_id",
    "cols.id",
    "col_groups.col_group",
    "col_groups.id",
  );

  // Handle geometry - adds col_areas.col_area to GROUP BY
  const needsGeometry =
    req.query.format && acceptedFormats.geo[req.query.format];
  if (needsGeometry) {
    if (req.query.shape) {
      geo =
        ", ST_AsGeoJSON(ST_Intersection(col_areas.col_area, ST_MakeValid(:shape))) geojson";
      params["shape"] = req.query.shape;
    } else {
      geo = ", ST_AsGeoJSON(col_areas.col_area) geojson";
    }
    groupByClauses.push("col_areas.col_area");
  }

  const joins = [
    "macrostrat.col_areas ON col_areas.col_id = cols.id",
    "macrostrat.col_groups ON col_groups.id = cols.col_group_id",
    "macrostrat.col_refs ON cols.id = col_refs.col_id",
  ];

  if (req.query.response === "long") {
    geo += ", p.project AS project_name";
    joins.push("macrostrat.projects p ON p.id = cols.project_id");
    groupByClauses.push("p.project");
  }

  const join_text = joins.map((d) => "LEFT JOIN " + d).join("\n");

  const sql = buildSQLQuery(
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
      ${join_text}`,
    {
      whereClauses,
      groupByClauses,
      orderByClauses,
      limit,
    },
  );

  const result = await larkin.queryPgAsync("macrostrat", sql, params);

  return result.rows;
}

function finalizeColumnsData(req, column_data, unit_data) {
  if (!column_data) return column_data;
  // Merge column and unit data

  return column_data
    .map((init): ColumnData | null => {
      let d = { ...init };
      if (typeof d.refs === "string" || d.refs instanceof String) {
        d.refs = larkin.jsonifyPipes(d.refs, "integers");
      }
      if (unit_data != null) {
        if (unit_data[d.col_id] == null) {
          // This column has no units that match the filters, so we should exclude it from the response
          return null;
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
      }
      return d;
    })
    .filter((d) => d !== null);
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
