var api = require("../api"),
    larkin = require("../larkin"),
    multiline = require("multiline"),
    dbgeo = require("dbgeo"),
    gp = require("geojson-precision");

module.exports = function(req, res, next, cb) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }

  var sql = `
  SELECT
    source_id,
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
    ${api.acceptedFormats.geo[req.query.format] ? ', web_geom AS geom' : ''}
  FROM maps.sources
  `

  var params = []
  var where = []

  if (req.query.source_id) {
    where.push("source_id = ANY($" + (where.length + 1) + ")");
    params.push(larkin.parseMultipleIds(req.query.source_id));
  }

  if (req.query.scale) {
    where.push("sources.scale = ANY($" + (where.length + 1) + ")");
    params.push(larkin.parseMultipleStrings(req.query.scale));
  }

  if (req.query.lat && req.query.lng) {
    where.push("ST_Intersects(ST_SetSRID(sources.rgeom, 4326), ST_GeomFromText($" + (where.length + 1) + ", 4326))");
    params.push("POINT(" + req.query.lng + " " + req.query.lat + ")");
  }

  if (req.query.shape) {
    var buffer = (req.query.buffer && !isNaN(parseInt(req.query.buffer))) ? parseInt(req.query.buffer)*1000 : 1;

    where.push("ST_Intersects(ST_SetSRID(sources.rgeom, 4326), ST_SetSRID(ST_Buffer($" + (where.length + 1) + "::geography , $" + (where.length + 2) + ")::geometry, 4326))");

    params.push("SRID=4326;" + decodeURI(req.query.shape), buffer);
  }

  // Remove any empty sources and etopo1
  where.push("sources.rgeom IS NOT NULL");

  sql += (where.length) ? (" WHERE " + where.join(" AND ")) : "";

  if (api.acceptedFormats.geo[req.query.format]) {
    sql += " ORDER BY CASE scale when 'tiny' THEN 1 WHEN 'small' THEN 2 WHEN 'medium' THEN 3 WHEN 'large' THEN 4 ELSE 5 END";
  } else {
    sql += " ORDER BY source_id";
  }

  if ("sample" in req.query) {
    sql += " LIMIT 5";
  }

  larkin.queryPg("burwell", sql, params, function(error, result) {
    if (error) {
      if (cb) {
        return cb(error);
      } else {
        return larkin.error(req, res, next, error);
      }
    } else {
      if (req.query.format && api.acceptedFormats.geo[req.query.format]) {
        dbgeo.parse(result.rows, {
          "geometryType": "geojson",
          "outputFormat": larkin.getOutputFormat(req.query.format),
          "precision": 5
        }, function(error, geojson) {
          if (error) {
            larkin.error(req, res, next, error);
          } else {
            if (cb) {
              cb(null, geojson);
            } else {
              larkin.sendData(req, res, next, {
                format: (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json",
                bare: (api.acceptedFormats.bare[req.query.format]) ? true : false
              }, {
                data: geojson
              });
            }

          }
        });
      } else {
        if (cb) {
          cb(null, result.rows);
        } else {
          larkin.sendData(req, res, next, {
            format: (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json",
            bare: (api.acceptedFormats.bare[req.query.format]) ? true : false
          }, {
            data: result.rows
          });
        }

      }

    }
  });
}
