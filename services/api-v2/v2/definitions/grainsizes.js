var api = require("../api"),
    larkin = require("../larkin");

module.exports = function(req, res, next, cb) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }

  let sql = `
    SELECT
      grain_id,
      grain_symbol,
      grain_name,
      COALESCE(grain_group, '') AS grain_group,
      COALESCE(soil_group, '') AS soil_group,
      min_size,
      max_size,
      classification
    FROM macrostrat.grainsize
  `
  let where = []
  let params = []

  if (req.query.grain_id) {
    where.push(`grain_id = ANY($${where.length + 1})`)
    params.push(req.query.grain_id.split(','))
  }
  if (req.query.grain_symbol) {
    where.push(`grain_symbol ILIKE ANY($${where.length + 1})`)
    params.push(req.query.grain_symbol.split(','))
  }
  if (req.query.grain_name) {
    where.push(`grain_name ILIKE ANY($${where.length + 1})`)
    params.push(req.query.grain_name.split(','))
  }
  if (req.query.grain_group) {
    where.push(`grain_group ILIKE ANY($${where.length + 1})`)
    params.push(req.query.grain_group.split(','))
  }
  if (req.query.soil_group) {
    where.push(`soil_group ILIKE ANY($${where.length + 1})`)
    params.push(req.query.soil_group.split(','))
  }
  if (req.query.classification) {
    where.push(`classification ILIKE ANY($${where.length + 1})`)
    params.push(req.query.classification.split(',').map(d => { return `%${d}%`}))
  }

  if (where.length) {
    sql += ` WHERE ${where.join(' AND ')}`
  }

  if ('sample' in req.query) {
    sql += ' LIMIT 5'
  }

  larkin.queryPg('burwell', sql, params, function(error, data) {
    if (error) {
      if (cb) {
        cb(error);
      } else {
        return larkin.error(req, res, next, error);
      }
    }

    if (cb) {
      cb(null, data.rows);
    } else {
      larkin.sendData(req, res, next, {
        format: (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json",
        bare: (api.acceptedFormats.bare[req.query.format]) ? true : false
      }, {
        data: data.rows
      });
    }

  });
}
