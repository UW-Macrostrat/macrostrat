var api = require("../api"),
    larkin = require("../larkin");

module.exports = function(req, res, next) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }
  
  var format = (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json";
  larkin.query("SELECT id AS project_id, project, timescale_id FROM projects", [], null, true, res, format, next);
}
