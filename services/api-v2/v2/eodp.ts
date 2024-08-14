var api = require("./api");
var dbgeo = require("dbgeo");
var larkin = require("./larkin");

module.exports = function (req, res, next) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }

  var geo =
    req.query.format && api.acceptedFormats.geo[req.query.format]
      ? true
      : false;

  var sql = `
    SELECT col_groups.col_group,
           ob.site_hole,
           date_started,
           ref_id,
           ob.col_id,
           lat::float,
           lng::float,
           STRING_AGG(ob.top_depth::text, '|' ORDER BY top_depth) top_depth,
           STRING_AGG(ob.bottom_depth::text,'|' ORDER BY top_depth) bottom_depth,
           STRING_AGG(trim(concat_WS(' ',principal_lith_prefix_cleaned,cleaned_lith,principal_lith_suffix_cleaned)),'|' ORDER BY top_depth) as primary_lith,
           STRING_AGG(lith_id::text,'|' ORDER BY top_depth) as lith_id,
            STRING_AGG(standard_minor_lith,'|' ORDER BY top_depth) as minor_lith
    FROM macrostrat_temp.offshore_baggage ob 
        JOIN macrostrat_temp.offshore_sites USING (col_id) 
        JOIN macrostrat_temp.col_groups on col_group_id=col_groups.id
  `;
  var where = [];
  var params = {};

  if (req.query.epoch) {
    where.push("epoch = ANY(:epoch)");
    params["epoch"] = larkin.parseMultipleStrings(req.query.epoch);
  }

  if (req.query.leg) {
    where.push("leg = ANY(:leg)");
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
    sql += ` WHERE ${where.join(" AND ")} AND lith_id>0\n `;
  } else {
    sql += ` WHERE lith_id>0\n `;
  }

  sql += " GROUP BY col_groups.col_group, ob.site_hole, offshore_sites.date_started,\n" +
      "offshore_sites.ref_id, ob.col_id, offshore_sites.lat, offshore_sites.lng ";

  if ("sample" in req.query) {
    sql += " LIMIT 1";
  }


  larkin.queryPg("burwell",sql, params, function (error, response) {
    if (error) {
      larkin.error(req, res, next, error);
    } else {
      //all parameter isn't formatted properly.

      if (req.query.format === undefined || req.query.format !== "csv") {
        for (var i = 0; i < response.rows.length; i++) {
          response.rows[i].top_depth = larkin.jsonifyPipes(
            response.rows[i].top_depth,
            "floats",
          );
          response.rows[i].bottom_depth = larkin.jsonifyPipes(
            response.rows[i].bottom_depth,
            "floats",
          );
          response.rows[i].primary_lith = larkin.jsonifyPipes(
            response.rows[i].primary_lith,
            "strings",
          );
          response.rows[i].lith_id = larkin.jsonifyPipes(
            response.rows[i].lith_id,
            "integers",
          );
          response.rows[i].minor_lith = larkin.jsonifyPipes(
            response.rows[i].minor_lith,
            "strings",
          );
        }
      }

      if (geo) {
        dbgeo.parse(
          response,
          {
            outputFormat: larkin.getOutputFormat(req.query.format),
            geometryColumn: ["lng", "lat"],
            geometryType: "ll",
          },
          function (error, response) {
            if (error) {
              larkin.error(req, res, next, "Something went wrong");
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
                  refs: "refs",
                },
                {
                  data: response.rows,
                },
              );
            }
          },
        );
      } else {
        //TODO determine why the all parameter returns 503 results rather than 505 as in prod
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
            data: response.rows,
          },
        );
      }
    }
  });
};
