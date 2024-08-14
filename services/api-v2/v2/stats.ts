var api = require("./api"),
  larkin = require("./larkin"),
  multiline = require("multiline");

module.exports = function (req, res, next) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }

  var sql = multiline(function () {
    /*
    SELECT
      project_id,
      project,
      columns::integer,
      packages::integer,
      units::integer,
      pbdb_collections::integer,
      measurements::integer,
      burwell_polygons::integer AS t_polys
    FROM macrostrat_temp.stats
  */
  });

  var format = api.acceptedFormats.standard[req.query.format]
    ? req.query.format
    : "json";

  larkin.queryPg("burwell", sql, [], function (error, data) {
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
        },
        {
          data: data.rows,
        },
      );
    }
  });
};
