const larkin = require("../larkin");

type Params = Record<
  string,
  string | number | boolean | Array<string | number | boolean>
>;

function buildProjectsFilter(req, field = "project_id"): [string[], Params] {
  const params: Params = {};
  const whereClauses: string[] = [];

  if (!larkin.hasCapability("composite-projects")) {
    // If composite projects are not supported, default to active projects only
    if (req.query.project_id) {
      whereClauses.push(field + " = ANY(:project_id)");
      params["project_id"] = req.query.project_id;
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

module.exports = {
  buildProjectsFilter,
};
