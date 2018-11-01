'use strict'

const larkin = require('../larkin')

module.exports = (req, res, next) => {
  const validFilters = [
    'lith_class',
    'lith_type',
    'lith',
    'lith_id',
    'strat_name_id',
    'concept_id'
  ]

  let where = []
  let params = []
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
