var api = require("./api"),
    larkin = require("./larkin");

module.exports = function(req, res, next) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }

  var sql = "\
    SELECT project, COUNT(distinct units_sections.section_id) AS packages, COUNT(distinct unit_id) AS units, COUNT(distinct collection_no) AS pbdb_collections FROM units_sections \
        JOIN cols ON cols.id = col_id \
        JOIN projects ON projects.id = project_id \
        LEFT JOIN pbdb_matches USING (unit_id) \
        WHERE project IN ('North America','New Zealand','Caribbean','Deep Sea') and status_code='active' \
        GROUP BY project_id";

  var format = (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json";

  larkin.query(sql, [], null, true, res, format, next);
}
