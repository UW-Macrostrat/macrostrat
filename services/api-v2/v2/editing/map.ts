var api = require("../api"),
  dbgeo = require("dbgeo"),
  larkin = require("../larkin");

module.exports = function (req, res, next) {
  if (req.query.id) {
    // return just that polygons and the ones that touch it
    larkin.queryPg(
      "macrostrat_editing",
      "SELECT b.col_id, ST_AsGeoJSON(b.geom) AS geometry FROM col_areas AS a JOIN col_areas AS b ON ST_Intersects(st_snaptogrid(a.geom,0.001), st_snaptogrid(b.geom,0.001)) WHERE a.col_id = $1 OR b.col_id = $1 GROUP BY b.col_id, b.geom ORDER BY b.col_id ASC;",
      [req.query.id],
      function (error, result) {
        dbgeo.parse({
          data: result.rows,
          outputFormat: "geojson",
          callback: function (error, result) {
            if (error) {
              larkin.error(req, res, next, error);
            } else {
              larkin.sendData(result, res, null, next);
            }
          },
        });
      },
    );
  } else {
    // return all polygons
    larkin.queryPg(
      "macrostrat_editing",
      "SELECT col_id, ST_AsGeoJSON(geom) as geometry FROM col_areas",
      [],
      function (error, result) {
        dbgeo.parse({
          data: result.rows,
          outputFormat: "geojson",
          callback: function (error, result) {
            if (error) {
              larkin.error(req, res, next, error);
            } else {
              larkin.sendData(result, res, null, next);
            }
          },
        });
      },
    );
  }
};
