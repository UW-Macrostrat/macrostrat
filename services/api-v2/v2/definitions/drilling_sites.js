var api = require("../api")
var larkin = require("../larkin")
var dbgeo = require('dbgeo')

module.exports = function(req, res, next, cb) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next)
  }

  var sql = `
    SELECT
      epoch,leg,site,hole,lat,lng,col_id,col_group_id,penetration,cored,recovered,recovery,drilled_interval,drilled_intervals,cores,date_started,date_finished,comments,ref_id
    FROM offshore_sites
  `
  var where = []
  var params = {}

  if (req.query.epoch) {
    where.push("epoch in (:epoch)")
    params["epoch"] = larkin.parseMultipleStrings(req.query.epoch)
  }

  if (req.query.leg) {
    where.push("exp in (:leg)")
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

  if ("sample" in req.query) {
    sql += " LIMIT 5"
  }

console.log(sql);

  larkin.query(sql, params, function(error, result) {
    if (error) {
      if (cb) {
        cb(error)
      } else {
        return larkin.error(req, res, next, error)
      }
    }

    // if a geographic format is requested
    if (req.query.format && api.acceptedFormats.geo[req.query.format]) {
      dbgeo.parse(result, {
        'geometryType': 'll',
        'geometryColumn': ['lng', 'lat'],
        'outputFormat': larkin.getOutputFormat(req.query.format),
        'precision': 6
      }, (error, geoResult) => {
        if (error) {
          if (cb) {
            return cb(error)
          }
          return larkin.error(req, res, next, 'Internal error', 500)
        }

        larkin.sendData(req, res, next, {
          format: (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json",
          bare: (api.acceptedFormats.bare[req.query.format]) ? true : false,
          refs: 'ref_id'
        }, {
          data: geoResult
        })
      })
    } else {
      larkin.sendData(req, res, next, {
        format: (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json",
        bare: (api.acceptedFormats.bare[req.query.format]) ? true : false,
        refs: 'ref_id'
      }, {
        data: result
      })
    }

  })
}
