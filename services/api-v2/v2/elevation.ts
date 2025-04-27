"use strict";
const api = require("./api");
const larkin = require("./larkin");

module.exports = (req, res, next, cb) => {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }
  let param = {};

  if ((req.query.lat && req.query.lng) || "sample" in req.query) {
    let lat = req.query.lat || 43.07;
    let lng = larkin.normalizeLng(req.query.lng) || -89.4;
    param["point"] = `POINT(${lng} ${lat})`;
    let sql = `WITH first AS (
          SELECT ST_Value(rast, 1, ST_GeomFromText(:point, 4326)) AS elevation, 1 as priority
          FROM sources.srtm1
          WHERE ST_Intersects(ST_GeomFromText(:point, 4326), rast)
          UNION ALL
          SELECT ST_Value(rast, 1, ST_GeomFromText(:point, 4326)) AS elevation, 2 as priority
          FROM sources.etopo1
          WHERE ST_Intersects(ST_GeomFromText(:point, 4326), rast)
      )
      SELECT elevation
      FROM first
      WHERE elevation IS NOT NULL
      ORDER BY priority ASC
      LIMIT 1`;

    larkin.queryPg("elevation", sql, param, (error, result) => {
      if (error) {
        if (cb) return cb(error);
        return larkin.error(req, res, next, "Error fetching elevation data");
      }
      if (cb) return cb(null, result.rows);
      larkin.sendData(
        req,
        res,
        next,
        {
          format: api.acceptedFormats.standard[req.query.format]
            ? req.query.format
            : "json",
          compact: true,
        },
        {
          data: result.rows,
        },
      );
    });
  } else if (
    req.query.start_lng &&
    req.query.start_lat &&
    req.query.end_lng &&
    req.query.end_lat
  ) {
    req.query.start_lng = larkin.normalizeLng(req.query.start_lng);
    req.query.end_lng = larkin.normalizeLng(req.query.end_lng);

    let leftLng =
      req.query.start_lng < req.query.end_lng
        ? req.query.start_lng
        : req.query.end_lng;
    let leftLat =
      req.query.start_lng < req.query.end_lng
        ? req.query.start_lat
        : req.query.end_lat;
    let rightLng =
      req.query.start_lng < req.query.end_lng
        ? req.query.end_lng
        : req.query.start_lng;
    let rightLat =
      req.query.start_lng < req.query.end_lng
        ? req.query.end_lat
        : req.query.start_lat;
    let params = {};

    params["linestring"] =
      `SRID=4326;LINESTRING(${leftLng} ${leftLat}, ${rightLng} ${rightLat})`;
    params["westPoint"] = `SRID=4326;POINT(${leftLng} ${leftLat})`;

    let sql = `WITH first AS (
        SELECT ST_SetSRID((ST_Dump(
        ST_LocateAlong(
          ST_AddMeasure(my_line, 0, 200), generate_series(0, 200)
        )
        )).geom, 4326) AS geom FROM (
          SELECT ST_GeomFromText(:linestring) AS my_line
        ) q
      )
      
      SELECT
        ST_X(geom) AS lng,
        ST_Y(geom) AS lat,
        round((ST_DistanceSphere(geom, :westPoint) * 0.001)::numeric, 2)::float AS d,
        (
          SELECT elevation
          FROM (
              SELECT ST_Value(rast, 1, geom) AS elevation, 1 as priority
              FROM sources.srtm1
              WHERE ST_Intersects(geom, rast)
              UNION ALL
              SELECT ST_Value(rast, 1, geom) AS elevation, 2 as priority
              FROM sources.etopo1
              WHERE ST_Intersects(geom, rast)
          ) first
          WHERE elevation IS NOT NULL AND elevation != 0
          ORDER BY priority ASC
          LIMIT 1
        ) AS elevation
      FROM first`;
    larkin.queryPg("elevation", sql, params, (error, result) => {
      if (error) {
        if (cb) return cb(error);
        return larkin.error(req, res, next, "Internal error", 500);
      }
      if (cb) return cb(null, result.rows);
      larkin.sendData(
        req,
        res,
        next,
        {
          format: api.acceptedFormats.standard[req.query.format]
            ? req.query.format
            : "json",
          compact: true,
        },
        {
          data: result.rows,
        },
      );
    });
  } else {
    return larkin.error(req, res, next, "Invalid Parameters", 401);
  }
};
