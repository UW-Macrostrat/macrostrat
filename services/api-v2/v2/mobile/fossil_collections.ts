var api = require("../api"),
  larkin = require("../larkin");

module.exports = function (req, res, next) {
  if (req.query.unit_id || "sample" in req.query) {
    if ("sample" in req.query) {
      req.query.unit_id = 15176;
    }
    larkin.queryPg("burwell",
      "SELECT DISTINCT collection_no AS cltn_id, collection_name AS cltn_name FROM macrostrat.pbdb_matches WHERE unit_id = ? AND occs > 0 and release_date<NOW()",
      [req.query.unit_id],
      function (error, result) {
        if (error) {
          larkin.error(req, res, next, error);
        } else {
          larkin.sendData(
            req,
            res,
            next,
            {
              format: api.acceptedFormats.standard[req.query.format]
                ? req.query.format
                : "json",
              bare: api.acceptedFormats.bare[req.query.format] ? true : false,
              compact: true,
            },
            {
              data: result.rows,
            },
          );
        }
      },
    );
  } else {
    larkin.info(req, res, next);
  }
};
