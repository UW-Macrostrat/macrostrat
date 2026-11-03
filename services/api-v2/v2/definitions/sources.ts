var api = require("../api"),
  larkin = require("../larkin"),
  dbgeo = require("dbgeo"),
  gp = require("geojson-precision");

module.exports = function (req, res, next, cb) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }

  var params = [];
  var where = [];

  if (req.query.source_id) {
    where.push("sources.source_id = ANY($" + (where.length + 1) + ")");
    params.push(larkin.parseMultipleIds(req.query.source_id));
  }

  if (req.query.scale) {
    where.push("sources.scale = ANY($" + (where.length + 1) + ")");
    params.push(larkin.parseMultipleStrings(req.query.scale));
  }

  // The exact test reads the footprint by key, so it runs after the cheap filters:
  // on `ma` it would test every compilation's footprint the box finds.
  var footprint =
    "(SELECT geometry FROM map_bounds.map_area WHERE id = sources.source_id)";

  if (req.query.lat && req.query.lng) {
    params.push("POINT(" + req.query.lng + " " + req.query.lat + ")");
    var point = "ST_GeomFromText($" + params.length + ", 4326)";
    where.push("ma.geometry && " + point);
    where.push("ST_Intersects(" + footprint + ", " + point + ")");
  }

  if (req.query.shape) {
    var buffer =
      req.query.buffer && !isNaN(parseInt(req.query.buffer))
        ? parseInt(req.query.buffer) * 1000
        : 1;

    params.push("SRID=4326;" + decodeURI(req.query.shape), buffer);
    var shape =
      "ST_SetSRID(ST_Buffer($" +
      (params.length - 1) +
      "::geography , $" +
      params.length +
      ")::geometry, 4326)";
    where.push("ma.geometry && " + shape);
    where.push("ST_Intersects(" + footprint + ", " + shape + ")");
  }

  // Remove any empty sources and etopo1
  // Maps only: v2 knows nothing of compilations. A mosaic (SGMC) is a map.
  where.push(
    "NOT (map_bounds.is_compilation(sources.source_id) AND NOT map_bounds.is_mosaic(sources.source_id))",
  );
  where.push("sources.web_geom IS NOT NULL");
  where.push("sources.status_code = 'active'");
  where.push("sources.is_finalized = true");

  var sql = `
  SELECT
    sources.source_id,
    name,
    COALESCE(url, '') url,
    COALESCE(ref_title, '') ref_title,
    COALESCE(authors, '') authors,
    COALESCE(ref_year, '') ref_year,
    COALESCE(ref_source, '') ref_source,
    COALESCE(isbn_doi, '') isbn_doi,
    COALESCE(scale, '') scale,
    features,
    area
    ${api.acceptedFormats.geo[req.query.format] ? ", web_geom AS geom" : ""}
  FROM maps.sources
  JOIN map_bounds.map_area ma ON ma.id = sources.source_id
  JOIN (values
    ('tiny', 0),
    ('small', 1),
    ('medium', 2),
    ('large', 3)
   ) ord (s, ordering) ON sources.scale = ord.s
   ${where.length ? " WHERE " + where.join(" AND ") : ""}
   ORDER BY ordering, new_priority
   ${"sample" in req.query ? "LIMIT 5" : ""}
  `;
  larkin.queryPg("burwell", sql, params, function (error, result) {
    if (error) {
      if (cb) {
        return cb(error);
      } else {
        return larkin.error(req, res, next, error);
      }
    } else {
      if (req.query.format && api.acceptedFormats.geo[req.query.format]) {
        dbgeo.parse(
          result.rows,
          {
            outputFormat: larkin.getOutputFormat(req.query.format),
            precision: 5,
          },
          function (error, geojson) {
            if (error) {
              larkin.error(req, res, next, error);
            } else {
              if (cb) {
                cb(null, geojson);
              } else {
                larkin.sendData(
                  req,
                  res,
                  next,
                  {
                    format: api.acceptedFormats.standard[req.query.format]
                      ? req.query.format
                      : "json",
                    bare: api.acceptedFormats.bare[req.query.format]
                      ? true
                      : false,
                  },
                  {
                    data: geojson,
                  },
                );
              }
            }
          },
        );
      } else {
        if (cb) {
          cb(null, result.rows);
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
              data: result.rows,
            },
          );
        }
      }
    }
  });
};
