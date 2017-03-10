var api = require("../api")
var larkin = require("../larkin")

module.exports = function(req, res, next, cb) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next)
  }

  var sql = `
    SELECT
      liths.id AS lith_id,
      lith AS name,
      lith_type AS type,
      COALESCE(lith_group, '') AS 'group',
      lith_class AS 'class',
      lith_color AS color,
      lith_fill AS fill,
      COUNT(distinct units_sections.unit_id) AS t_units
    FROM liths
    LEFT JOIN unit_liths ON unit_liths.lith_id = liths.id
    LEFT JOIN units_sections ON units_sections.unit_id = unit_liths.unit_id
  `
  var where = []
  var params = {}

  if (req.query.lith_class) {
    where.push("lith_class IN (:lith_class)")
    params["lith_class"] = larkin.parseMultipleStrings(req.query.lith_class)
  }
  if (req.query.lith_type){
    where.push("lith_type IN (:lith_type)")
    params["lith_type"] = larkin.parseMultipleStrings(req.query.lith_type)
  }
  if (req.query.lith) {
    where.push("lith IN (:lith)")
    params["lith"] = larkin.parseMultipleStrings(req.query.lith)
  }
  if (req.query.lith_id) {
    where.push("liths.id IN (:lith_id)")
    params["lith_id"] = larkin.parseMultipleIds(req.query.lith_id)
  }
  if (req.query.lith_like) {
    where.push("lith LIKE :lith")
    params["lith"] = req.query.lith_like + '%'
  }
  if (req.query.lith_group) {
    where.push("lith_group IN (:lith_group)")
    params["lith_group"] = larkin.parseMultipleIds(req.query.lith_group)
  }

  if (where.length) {
    sql += ` WHERE ${where.join(' AND ')}`
  }

  sql += " GROUP BY liths.id "

  if ("sample" in req.query) {
    sql += " LIMIT 5"
  }

  larkin.query(sql, params, function(error, data) {
    if (error) {
      if (cb) {
        cb(error)
      } else {
        return larkin.error(req, res, next, error)
      }
    }

    if (cb) {
      cb(null, data);
    } else {
      larkin.sendData(req, res, next, {
        format: (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json",
        bare: (api.acceptedFormats.bare[req.query.format]) ? true : false,
        compact: true
      }, {
        data: data
      })
    }
  })
}
