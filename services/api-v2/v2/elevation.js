var api = require('./api')
var larkin = require('./larkin')

module.exports = function(req, res, next, cb) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  } else {
    if ((req.query.lat && req.query.lng) || 'sample' in req.query) {
      var lat = req.query.lat || 43.07,
          lng = larkin.normalizeLng(req.query.lng) || -89.4;

      var point = "POINT(" + lng + " " + lat + ")";
      larkin.queryPg("elevation", "WITH first AS (SELECT ST_Value(rast, 1, ST_GeomFromText($1, 4326)) AS elevation FROM sources.srtm1 WHERE ST_Intersects(ST_GeomFromText($2, 4326), rast)) SELECT elevation FROM first WHERE elevation IS NOT NULL LIMIT 1", [point, point], function(error, result) {
        if (error) {
          if (cb) return cb(error);
          larkin.error(req, res, next, error);
        } else {
          if (cb) return cb(null, result.rows);
          larkin.sendData(req, res, next, {
            format: (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json",
            compact: true
          }, {
            data: result.rows
          });
        }
      });
    } else if (req.query.start_lng && req.query.start_lat && req.query.end_lng && req.query.end_lat) {
      req.query.start_lng = larkin.normalizeLng(req.query.start_lng)
      req.query.end_lng = larkin.normalizeLng(req.query.end_lng)

      var leftLng = (req.query.start_lng < req.query.end_lng) ? req.query.start_lng : req.query.end_lng
      var leftLat = (req.query.start_lng < req.query.end_lng) ? req.query.start_lat : req.query.end_lat
      var rightLng = (req.query.start_lng < req.query.end_lng) ? req.query.end_lng : req.query.start_lng
      var rightLat = (req.query.start_lng < req.query.end_lng) ? req.query.end_lat : req.query.start_lat

      var linestring = `LINESTRING(${leftLng} ${leftLat}, ${rightLng} ${rightLat})`
      larkin.queryPg('elevation', `
        WITH first AS (
          SELECT ST_SetSRID((ST_Dump(
          ST_LocateAlong(
            ST_AddMeasure(my_line, 0, 100), generate_series(0, 100)
          )
          )).geom, 4326) AS geom FROM (
            SELECT ST_GeomFromText($1) AS my_line
          ) q
        )

        SELECT DISTINCT ON (ST_X(geom), ST_Y(geom), ST_Value(rast, 1, geom)) ST_X(geom) AS lng, ST_Y(geom) AS lat, ST_Value(rast, 1, geom) AS elevation
        FROM first
        JOIN sources.srtm1 ON ST_Intersects(geom, rast)
      `, [linestring], function(error, result) {
        if (error) {
          if (cb) return cb(error);
          larkin.error(req, res, next, 'Internal error', 500)
        } else {
          if (cb) return cb(null, result.rows)
          larkin.sendData(req, res, next, {
            format: (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json",
            compact: true
          }, {
            data: result.rows
          })
        }
      })
    } else {
      return larkin.error(req, res, next, 'Invalid Parameters', 401)
    }


  }
}
