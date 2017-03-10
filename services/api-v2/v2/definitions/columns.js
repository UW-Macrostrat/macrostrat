var api = require("../api")
var larkin = require("../larkin")

module.exports = function(req, res, next, cb) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next)
  }

  var sql = `
    SELECT
      cols.id AS col_id,
      col_group_id,
      col_name,
      GROUP_CONCAT(DISTINCT ref_id SEPARATOR '|') AS ref_id,
      status_code AS status,
      count(distinct units_sections.unit_id) AS t_units,
      project_id
    FROM cols
    LEFT JOIN col_refs ON col_id = cols.id
    LEFT JOIN units_sections ON units_sections.col_id = cols.id
  `
  var where = []
  var params = {}

  if (req.query.col_id) {
    where.push("cols.id in (:col_id)")
    params["col_id"] = larkin.parseMultipleIds(req.query.col_id)
  }
  if (req.query.col_group_id) {
    where.push("cols.col_group_id IN (:col_group_id)")
    params["col_group_id"] = larkin.parseMultipleIds(req.query.col_group_id)
  }
  if (req.query.col_name) {
    where.push("cols.col_name IN (:col_name)")
    params["col_name"] = larkin.parseMultipleStrings(req.query.col_name)
  }
  if (req.query.project_id) {
   where.push("cols.project_id IN (:project_id)")
   params["project_id"] = larkin.parseMultipleIds(req.query.project_id)
  }
  if (req.query.status) {
    where.push("status_code = :status")
    params["status"] = req.query.status
  }

  if (where.length) {
    sql += ` WHERE ${where.join(' AND ')}`
  }

  sql += " GROUP BY cols.id"

  if ("sample" in req.query) {
    sql += " LIMIT 5"
  }

  larkin.query(sql, params, function(error, result) {
    if (error) {
      if (cb) {
        cb(error)
      } else {
        return larkin.error(req, res, next, error)
      }
    }

    result.forEach(function(d) {
      d.ref_id = larkin.jsonifyPipes(d.ref_id, "integers");
    })

    if (cb) {
      cb(null, result)
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
