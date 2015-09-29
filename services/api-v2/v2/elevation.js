var api = require("./api"),
    larkin = require("./larkin");

module.exports = function(req, res, next) {
  if (!req.query.lat && !req.query.lng && !("sample" in req.query)) {
    larkin.info(req, res, next);
  } else {
    var lat = req.query.lat || 43.07,
        lng = larkin.normalizeLng(req.query.lng) || -89.4;

    var point = "POINT(" + lng + " " + lat + ")";
    larkin.queryPg("burwell", "WITH first AS (SELECT ST_Value(rast, 1, ST_GeomFromText($1, 4326)) AS elevation FROM sources.etopo1 WHERE ST_Intersects(ST_GeomFromText($2, 4326), rast)) SELECT elevation FROM first WHERE elevation IS NOT NULL", [point, point], function(error, result) {
      if (error) {
        larkin.error(req, res, next, error);
      } else {
        larkin.sendCompact(result.rows, res, (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json", next);
      }
    });

  }
}
