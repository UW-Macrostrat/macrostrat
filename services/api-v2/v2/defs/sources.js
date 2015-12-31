var api = require("../api"),
    larkin = require("../larkin"),
    multiline = require("multiline"),
    dbgeo = require("dbgeo"),
    gp = require("geojson-precision");

module.exports = function(req, res, next) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }

  var sql = multiline(function() {/*
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
  */});

  if (api.acceptedFormats.geo[req.query.format]) {
    sql += ", ST_AsGeoJSON(bbox) AS geometry";
  }

  sql += " FROM maps.sources ";


  var params = [];
  var where = [];

  if (req.query.source_id) {
    where.push("source_id = ANY($" + (where.length + 1) + ")");
    params.push(larkin.parseMultipleIds(req.query.source_id));
  }

  if (req.query.scale) {
    where.push("sources.scale = ANY($" + (where.length + 1) + ")");
    params.push(larkin.parseMultipleStrings(req.query.scale));
  }

  if (req.query.lat && req.query.lng) {
    where.push("ST_Intersects(sources.bbox, ST_GeomFromText($" + (where.length + 1) + ", 4326))");
    params.push("POINT(" + req.query.lng + " " + req.query.lat + ")");
  }

  if (req.query.shape) {
    var buffer = (req.query.buffer && !isNaN(parseInt(req.query.buffer))) ? parseInt(req.query.buffer)*1000 : 1;

    where.push("ST_Intersects(sources.bbox, ST_Buffer($" + (where.length + 1) + "::geography , $" + (where.length + 2) + ")::geometry)");

    params.push("SRID=4326;" + decodeURI(req.query.shape), buffer);
  }

  // Remove any empty sources and etopo1
  where.push("sources.area IS NOT NULL");

  sql += (where.length) ? (" WHERE " + where.join(" AND ")) : "";
  sql += " ORDER BY source_id";

  if ("sample" in req.query) {
    sql += " LIMIT 5";
  }

  larkin.queryPg("burwell", sql, params, function(error, result) {
    if (error) {
      larkin.error(req, res, next, error);
    } else {
      if (req.query.format && api.acceptedFormats.geo[req.query.format]) {
        dbgeo.parse({
          "data": result.rows,
          "outputFormat": larkin.getOutputFormat(req.query.format)
        }, function(error, geojson) {
          if (error) {
            larkin.error(req, res, next, error);
          } else {
            if (larkin.getOutputFormat(req.query.format) === "geojson") {
              result = gp(geojson, 5);
            }
            larkin.sendData(req, res, next, {
              format: (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json",
              bare: (api.acceptedFormats.bare[req.query.format]) ? true : false
            }, {
              data: geojson
            });
          }
        });
      } else {
        larkin.sendData(req, res, next, {
          format: (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json",
          bare: (api.acceptedFormats.bare[req.query.format]) ? true : false
        }, {
          data: result.rows
        });
      }

    }
  });
}
