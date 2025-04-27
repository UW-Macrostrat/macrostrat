var api = require("../api");
var larkin = require("../larkin");
var dbgeo = require("dbgeo");

module.exports = function (req, res, next, cb) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }

  var sql = `
    SELECT
      epoch,
      leg,
      site,
      hole,lat::float,
      lng::float,
      col_id,
      col_group_id,
      penetration,
      cored,
      recovered,
      recovery,
      drilled_interval,
      drilled_intervals,
      cores,
      date_started,
      date_finished,
      comments,
      ref_id
    FROM macrostrat.offshore_sites
  `;
  var where = [];
  var params = {};

  if (req.query.epoch) {
    where.push("epoch = ANY(:epoch)");
    params["epoch"] = larkin.parseMultipleStrings(req.query.epoch);
  }

  if (req.query.leg) {
    where.push("exp = ANY(:leg)");
    params["leg"] = larkin.parseMultipleStrings(req.query.leg);
  }
  if (req.query.site) {
    where.push("site = ANY(:site)");
    params["site"] = larkin.parseMultipleStrings(req.query.site);
  }

  if (req.query.col_id) {
    where.push("col_id = ANY(:col_id)");
    params["col_id"] = larkin.parseMultipleIds(req.query.col_id);
  }

  if (req.query.col_group_id) {
    where.push("site = ANY(:col_group_id)");
    params["col_group_id"] = larkin.parseMultipleIds(req.query.col_group_id);
  }

  if (where.length) {
    sql += ` WHERE ${where.join(" AND ")}`;
  }

  if ("sample" in req.query) {
    sql += " LIMIT 5";
  }
  console.log(
    "print format BEFORE submitting query",
    api.acceptedFormats.geo[req.query.format],
  );
  console.log("printing params before they go through larkin", params);

  larkin.queryPg("burwell", sql, params, function (error, result) {
    if (error) {
      if (cb) {
        cb(error);
      } else {
        return larkin.error(req, res, next, error);
      }
    }

    // if a geographic format is requested
    if (req.query.format && api.acceptedFormats.geo[req.query.format]) {
      //there is an error here we need to figure out
      console.log("printing results before geoparse", result);
      dbgeo.parse(
        result.rows,
        {
          geometryType: "ll",
          geometryColumn: ["lng", "lat"],
          outputFormat: larkin.getOutputFormat(req.query.format),
          precision: 6,
        },
        (error, geoResult) => {
          if (error) {
            if (cb) {
              return cb(error);
            }
            return larkin.error(req, res, next, "Internal error", 500);
          }
          //send results for geo format
          larkin.sendData(
            req,
            res,
            next,
            {
              format: api.acceptedFormats.standard[req.query.format]
                ? req.query.format
                : "json",
              bare: api.acceptedFormats.bare[req.query.format] ? true : false,
              refs: "ref_id",
            },
            {
              data: geoResult,
            },
          );
        },
      );
    }
    //send results if no geo format requested.
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
          refs: "ref_id",
        },
        {
          data: result.rows,
        },
      );
    }
  });
};
