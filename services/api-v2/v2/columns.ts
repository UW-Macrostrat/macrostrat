import {
  buildSQLQuery,
  getColumnFilters,
  getColumnIDsForQuery,
  getUnitsData,
} from "./units";

import dbgeo from "dbgeo";
import * as larkin from "./larkin";
import _ from "underscore";
import gp from "geojson-precision";
import { acceptedFormats } from "./api";
import { sharedUnitFilters } from "./defs";
import { buildProjectsFilter } from "./utils";

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
    getColumnFilters(req);

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

  // Handle status code
  if (req.query.status_code) {
    params["status_code"] = larkin.parseMultipleStrings(
      decodeURI(req.query.status_code),
    );
  } else {
    params["status_code"] = ["active"];
  }
  whereClauses.push("cols.status_code::text = ANY(:status_code::text[])");

  const [projectFilters, projectParams] = buildProjectsFilter(
    req,
    "cols.project_id",
  );
  whereClauses = whereClauses.concat(projectFilters);
  params = { ...params, ...projectParams };

  /**
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
    */
  //
  // if (new_cols == null) {
  //   // We have to filter directly instead of relying on units filtering
  //
  //   if ("col_group_id" in req.query) {
  //     whereClauses.push("cols.col_group_id = :col_group_id");
  //     params["col_group_id"] = req.query.col_group_id;
  //   }
  //   if ("lat" in req.query && "lng" in req.query) {
  //     const point = `ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)`;
  //     whereClauses.push(`ST_Contains(col_areas.col_area, ${point})`);
  //     params["lat"] = req.query.lat;
  //     params["lng"] = larkin.normalizeLng(req.query.lng);
  //   }
  //   if ("col_type" in req.query) {
  //     whereClauses.push("cols.col_type = :col_type");
  //     params["col_type"] = req.query.col_type;
  //   }
  //   if ("project_id" in req.query) {
  //     whereClauses.push("cols.project_id = :project_id");
  //     params["project_id"] = req.query.project_id;
  //   }
  // }

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
             LEFT JOIN macrostrat.col_areas on col_areas.col_id = cols.id
             LEFT JOIN macrostrat.col_groups ON col_groups.id = cols.col_group_id
             LEFT JOIN macrostrat.col_refs ON cols.id = col_refs.col_id`,
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
  return column_data.map((init) => {
    let d = { ...init };
    if (typeof d.refs === "string" || d.refs instanceof String) {
      d.refs = larkin.jsonifyPipes(d.refs, "integers");
    }
    if (unit_data != null) {
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
