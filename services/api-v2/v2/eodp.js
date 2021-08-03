var api = require('./api')
var dbgeo = require('dbgeo')
var larkin = require('./larkin')

module.exports = function(req, res, next) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }

  var geo = (req.query.format && api.acceptedFormats.geo[req.query.format]) ? true : false;

  var sql = `
    SELECT col_groups.col_group,ob.site_hole,date_started,ref_id,ob.col_id,lat,lng,GROUP_CONCAT(ob.top_depth ORDER BY top_depth SEPARATOR '|') top_depth,GROUP_CONCAT(ob.bottom_depth ORDER BY top_depth SEPARATOR '|') bottom_depth, GROUP_CONCAT(trim(concat_WS(' ',principal_lith_prefix_cleaned,cleaned_lith,principal_lith_suffix_cleaned)) ORDER BY top_depth SEPARATOR '|') as primary_lith,GROUP_CONCAT(trim(concat_WS(' ',minor_lith_prefix_cleaned,cleaned_minor,minor_lithology_suffix)) ORDER BY top_depth SEPARATOR '|') as minor_lith FROM offshore_baggage ob JOIN offshore_sites USING (col_id) JOIN col_groups on col_group_id=col_groups.id
  `
  var where = []
  var params = {}

  if (req.query.epoch) {
    where.push("epoch in (:epoch)")
    params["epoch"] = larkin.parseMultipleStrings(req.query.epoch)
  }

  if (req.query.leg) {
    where.push("leg in (:leg)")
    params["leg"] = larkin.parseMultipleStrings(req.query.leg)
  }
  if (req.query.site) {
    where.push("site IN (:site)")
    params["site"] = larkin.parseMultipleStrings(req.query.site)
  }

  if (req.query.col_id) {
    where.push("col_id IN (:col_id)")
    params["col_id"] = larkin.parseMultipleIds(req.query.col_id)
  }

  if (req.query.col_group_id) {
    where.push("site IN (:col_group_id)")
    params["col_group_id"] = larkin.parseMultipleIds(req.query.col_group_id)
  }

  if (where.length) {
    sql += ` WHERE ${where.join(' AND ')}`
  }

  sql += " GROUP BY ob.col_id ORDER BY ob.col_id,ob.top_depth ASC "

  if ("sample" in req.query) {
    sql += " LIMIT 1"
  }

//console.log(sql);

  larkin.query(sql, params, function(error, response) {
    if (error) {
      larkin.error(req, res, next, error);
    } else {
      if (req.query.format !== "csv"){
        for (var i = 0; i < response.length; i++) {
          response[i].top_depth = larkin.jsonifyPipes(response[i].top_depth, "floats");
          response[i].bottom_depth = larkin.jsonifyPipes(response[i].bottom_depth, "floats");
          response[i].primary_lith = larkin.jsonifyPipes(response[i].primary_lith, "strings");
          response[i].minor_lith = larkin.jsonifyPipes(response[i].minor_lith, "strings");

        }
      }

      if (geo) {
          dbgeo.parse(response, {
            "outputFormat": larkin.getOutputFormat(req.query.format),
            "geometryColumn": ["lng", "lat"],
            "geometryType": "ll"
          }, function(error, response) {
              if (error) {
                larkin.error(req, res, next, "Something went wrong");
              } else {
                larkin.sendData(req, res, next, {
                  format: (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json",
                  bare: (api.acceptedFormats.bare[req.query.format]) ? true : false,
                  refs: "refs"
                }, {
                  data: response
                });
              }
            }
          );
      } else { larkin.sendData(req, res, next, {
        format: (api.acceptedFormats.standard[req.query.format]) ? req.query.format : 'json',
        bare: (api.acceptedFormats.bare[req.query.format]) ? true : false,
        refs: 'ref_id'
      }, {
        data: response
        })
        }
    }
  })
}
