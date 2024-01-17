var api = require("./api");
var larkin = require("./larkin");
var dbgeo = require("dbgeo");

module.exports = function (req, res, next) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }
  var where = [];
  var params = [];
  var limit = "";

  if ("sample" in req.query) {
    limit = " LIMIT 5";
  } else {
    limit = "";
  }

  if (req.query.point_id) {
    where.push("point_id = ANY($" + (where.length + 1) + ")");
    params.push(larkin.parseMultipleIds(req.query.point_id));
  }
  if (req.query.point_type) {
    where.push("point_type = ANY($" + (where.length + 1) + ")");
    params.push(larkin.parseMultipleStrings(req.query.point_type));
  }
  if (req.query.certainty) {
    where.push("certainty ILIKE $" + (where.length + 1));
    params.push("%" + req.query.certainty + "%");
  }
  if (req.query.comments) {
    where.push("comments ILIKE $" + (where.length + 1));
    params.push("%" + req.query.comments + "%");
  }
  if (req.query.source_id) {
    where.push("source_id = ANY($" + (where.length + 1) + ")");
    params.push(larkin.parseMultipleIds(req.query.source_id));
  }
  if (
    req.query.minlat &&
    req.query.minlng &&
    req.query.maxlat &&
    req.query.maxlng
  ) {
    where.push(
      "ST_Intersects(geom, ST_Envelope(ST_GeomFromText($" +
        (where.length + 1) +
        ")))",
    );
    params.push(
      "SRID=4326;LINESTRING(" +
        req.query.minlng +
        " " +
        req.query.minlat +
        "," +
        req.query.maxlng +
        " " +
        req.query.maxlat +
        ")",
    );
  }

  if (!where.length && !limit.length) {
    return larkin.error(
      req,
      res,
      next,
      "No valid query parameters passed",
      400,
    );
  } else if (!where.length && limit.length) {
    where = "";
  } else {
    where = "WHERE " + where.join(" AND ");
  }

  larkin.queryPg(
    "burwell",
    `
  SELECT
    point_id,
    strike,
    dip,
    dip_dir,
    COALESCE(point_type, '') AS point_type,
    COALESCE(certainty, '') AS certainty,
    COALESCE(comments, '') AS comments,
    ST_X(geom) AS longitude,
    ST_Y(geom) AS latitude,
    source_id
  FROM points.points
  ${where}
  ${limit}
  `,
    params,
    function (error, result) {
      if (error) {
        console.log(error);
        return larkin.error(req, res, next, "Something went wrong", 500);
      }

      if (req.query.format && req.query.format === "csv") {
        larkin.sendData(
          req,
          res,
          next,
          {
            format: "csv",
            bare: true,
            refs: "source_id",
          },
          {
            data: result.rows,
          },
        );
      } else {
        dbgeo.parse(
          result.rows,
          {
            outputFormat:
              req.query.format && api.acceptedFormats.geo[req.query.format]
                ? larkin.getOutputFormat(req.query.format)
                : "geojson",
            geometryType: "ll",
            geometryColumn: ["longitude", "latitude"],
            precision: 6,
          },
          function (error, output) {
            if (error) {
              return larkin.error(
                req,
                res,
                next,
                "An error occurred while parsing the output",
                500,
              );
            }
            larkin.sendData(
              req,
              res,
              next,
              {
                format: "json",
                bare: api.acceptedFormats.bare[req.query.format] ? true : false,
                refs: "source_id",
              },
              {
                data: output,
              },
            );
          },
        );
      }
    },
  );
};
