const larkin = require("../larkin");

type Params = Record<
  string,
  string | number | boolean | Array<string | number | boolean>
>;

export function buildProjectsFilter(
  req,
  field = "project_id",
): [string[], Params] {
  const params: Params = {};
  const whereClauses: string[] = [];

  if (!larkin.hasCapability("composite-projects")) {
    // If composite projects are not supported, default to active projects only
    if (req.query.project_id) {
      whereClauses.push(field + " = ANY(:project_id)");
      params["project_id"] = larkin.parseMultipleIds(req.query.project_id);
    }
    return [whereClauses, params];
  }

  // Newer handling of composite/core projects
  if (req.query.project_id) {
    if (req.query.project_id !== "all") {
      whereClauses.push(
        field + " = ANY(macrostrat.flattened_project_ids(:project_id))",
      );
      params["project_id"] = larkin.parseMultipleIds(req.query.project_id);
    }
  } else {
    // Default to active projects only
    whereClauses.push(field + " = ANY(macrostrat.core_project_ids())");
  }

  return [whereClauses, params];
}

export interface FilterStatements {
  withStatements?: Record<string, string>;
  whereClauses?: string[];
  orderByClauses?: string[];
  groupByClauses?: string[];
  limit?: number;
}

export function buildSQLQuery(
  baseQuery: string,
  filters: FilterStatements,
): string {
  const {
    withStatements = {},
    whereClauses = [],
    orderByClauses = [],
    groupByClauses = [],
    limit,
  } = filters;
  let sql = "";
  if (Object.keys(withStatements).length > 0) {
    const withStrings = [];
    for (const [key, value] of Object.entries(filters.withStatements)) {
      withStrings.push(`${key} AS (${value})`);
    }
    sql += `WITH ${dedupe(withStrings).join(", ")}\n`;
  }
  sql += baseQuery;
  if (whereClauses.length > 0) {
    sql += "\nWHERE " + dedupe(whereClauses).join("\nAND ");
  }

  if (groupByClauses.length > 0) {
    sql += "\nGROUP BY " + dedupe(groupByClauses).join(",\n");
  }

  if (orderByClauses.length > 0) {
    sql += "\nORDER BY " + dedupe(orderByClauses).join(",\n");
  }
  if (limit) {
    sql += `\nLIMIT ${limit} `;
  }

  return sql;
}

function dedupe(arr: any[]) {
  return Array.from(new Set(arr));
}
