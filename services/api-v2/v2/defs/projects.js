var api = require("../api"),
    larkin = require("../larkin");

module.exports = function(req, res, next) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }
  var sql = "SELECT projects.id AS project_id, project, timescale_id, COUNT(DISTINCT units_sections.unit_id) AS t_units FROM projects LEFT JOIN cols ON projects.id = cols.project_id LEFT JOIN units_sections ON units_sections.col_id = cols.id GROUP BY projects.id";

  if ("sample" in req.query) {
    sql += " LIMIT 5";
  }

  larkin.query(sql, [], function(error, data) {
    if (error) {
      return larkin.error(req, res, next, error);
    }

    larkin.sendData(req, res, next, {
      format: (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json",
      bare: (api.acceptedFormats.bare[req.query.format]) ? true : false
    }, {
      data: data
    });

  });
}
