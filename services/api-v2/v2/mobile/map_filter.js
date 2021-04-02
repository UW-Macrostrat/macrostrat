// note that this route will throw an error when displaying documentation page because trap for case of no parameters not in here

'use strict'
const larkin = require('../larkin')

module.exports = (req, res, next) => {
  let where = []
  let params = []
  // Normal (strict) liths
  if (req.query.lith_class) {
    where.push(`lith_classes && $${where.length + 1}`)
    params.push(req.query.lith_class.split(','))
  }
  if (req.query.lith_type) {
    where.push(`lith_types && $${where.length + 1}`)
    params.push(req.query.lith_type.split(','))
  }
  if (req.query.lith_id) {
    where.push(`lith_ids && $${where.length + 1}`)
    params.push(req.query.lith_id.split(','))
  }
  // All liths
  if (req.query.all_lith_class) {
    where.push(`all_lith_classes && $${where.length + 1}`)
    params.push(req.query.all_lith_class.split(','))
  }
  if (req.query.all_lith_type) {
    where.push(`all_lith_types && $${where.length + 1}`)
    params.push(req.query.all_lith_type.split(','))
  }
  if (req.query.all_lith_id) {
    where.push(`all_lith_ids && $${where.length + 1}`)
    params.push(req.query.all_lith_id.split(','))
  }
  // Strat names
  if (req.query.strat_name_id) {
    where.push(`strat_name_children && $${where.length + 1}`)
    params.push(req.query.strat_name_id.split(','))
  }
  if (req.query.concept_id) {
    where.push(`concept_ids && $${where.length + 1}`)
    params.push(req.query.concept_id.split(','))
  }

  let sql = `
    SELECT legend_id
    FROM maps.legend
    WHERE ${where.join(' AND ')}
  `
  larkin.queryPg('burwell', sql, params, (error, result) => {
    if (error) return larkin.error(req, res, next)
    res.json(result.rows.map(row => { return row.legend_id }).filter(d => { if (d) return d }))
  })
}
