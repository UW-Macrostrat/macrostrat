"use strict";
const api = require("./api");
const larkin = require("./larkin");

/*
Elevation at a point, or along a line.

Two implementations behind one response shape. With `ELEVATION_SERVICE_URL`
set (e.g. `https://tiles.macrostrat.org/elevation`), the answer comes from the
tile server's COG-backed elevation service; without it, from the legacy
`elevation` Postgres database — 143 GB of SRTM rasters that the service exists
to retire. The shapes are kept byte-compatible so `mobile/map_query_v2`,
`mobile/dashboard` and Rockd need no change:

  point:    [{ elevation }]                 ([] where nothing covers the point)
  profile:  [{ lng, lat, d, elevation }]    d in km from the western end
*/

const ELEVATION_SERVICE_URL = process.env.ELEVATION_SERVICE_URL;
const SERVICE_TIMEOUT_MS = 10000;

function serviceUrl(path, params) {
  const url = new URL(path, ELEVATION_SERVICE_URL.replace(/\/?$/, "/"));
  for (const [key, value] of Object.entries(params ?? {})) {
    url.searchParams.set(key, String(value));
  }
  return url;
}

async function fetchService(url) {
  const response = await fetch(url, {
    signal: AbortSignal.timeout(SERVICE_TIMEOUT_MS),
    headers: { accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(`Elevation service responded ${response.status}`);
  }
  return response.json();
}

// The legacy database returns no row where no raster covers the point; the
// service says so with a null. Keep the legacy "no rows" for callers that
// test `data.length`.
async function servicePoint(lng, lat) {
  const data = await fetchService(serviceUrl(`point/${lng},${lat}`));
  if (data.elevation == null) return [];
  return [{ elevation: data.elevation }];
}

async function serviceProfile(start, end) {
  const data = await fetchService(
    serviceUrl("profile", {
      start_lng: start.lng,
      start_lat: start.lat,
      end_lng: end.lng,
      end_lat: end.lat,
      samples: 201,
    }),
  );
  return data.samples.map((s) => ({
    lng: s.lng,
    lat: s.lat,
    // Legacy `d` is ST_DistanceSphere from the western end in km, two decimals.
    d: Math.round(s.distance / 10) / 1000,
    elevation: s.elevation ?? null,
  }));
}

module.exports = (req, res, next, cb) => {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }

  const respond = (rows) => {
    if (cb) return cb(null, rows);
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
        data: rows,
      },
    );
  };

  const fail = (error, message, code) => {
    if (cb) return cb(error);
    return larkin.error(req, res, next, message, code);
  };

  let param = {};

  if ((req.query.lat && req.query.lng) || "sample" in req.query) {
    let lat = req.query.lat || 43.07;
    let lng = larkin.normalizeLng(req.query.lng) || -89.4;

    if (ELEVATION_SERVICE_URL) {
      servicePoint(lng, lat)
        .then(respond)
        .catch((error) => fail(error, "Error fetching elevation data"));
      return;
    }

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
        return fail(error, "Error fetching elevation data");
      }
      respond(result.rows);
    });
  } else if (
    req.query.start_lng &&
    req.query.start_lat &&
    req.query.end_lng &&
    req.query.end_lat
  ) {
    req.query.start_lng = larkin.normalizeLng(req.query.start_lng);
    req.query.end_lng = larkin.normalizeLng(req.query.end_lng);

    // The profile has always run west to east regardless of the order given,
    // with `d` measured from the western end. Kept, so the response is the same
    // from either implementation.
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

    if (ELEVATION_SERVICE_URL) {
      serviceProfile(
        { lng: leftLng, lat: leftLat },
        { lng: rightLng, lat: rightLat },
      )
        .then(respond)
        .catch((error) => fail(error, "Internal error", 500));
      return;
    }

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
        return fail(error, "Internal error", 500);
      }
      respond(result.rows);
    });
  } else {
    return larkin.error(req, res, next, "Invalid Parameters", 401);
  }
};
