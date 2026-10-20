var api = require("./api"),
  larkin = require("./larkin");

module.exports = async function (req, res, next) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }

  const sql = `SELECT
      project_id,
      project,
      columns::integer,
      packages::integer,
      units::integer,
      pbdb_collections::integer,
      measurements::integer,
      burwell_polygons::integer AS t_polys
    FROM macrostrat.stats`;

  const format = api.acceptedFormats.standard[req.query.format]
    ? req.query.format
    : "json";

  try {
    const data = await larkin.queryPgAsync("burwell", sql, {});
    larkin.sendData(
      req,
      res,
      next,
      {
        format,
        bare: api.acceptedFormats.bare[req.query.format] ? true : false,
      },
      {
        data: data.rows,
      },
    );
  } catch (error) {
    larkin.error(req, res, next, error);
  }
};
