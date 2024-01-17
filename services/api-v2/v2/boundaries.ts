const larkin = require('./larkin')
const dbgeo = require('dbgeo')

module.exports = (req, res, next) => {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }

  if (!req.query.boundary_id) {
    return larkin.error(req, res, next)
  }
  req.query.boundary_id = req.query.boundary_id.split(',')

  larkin.queryPg('burwell', `
    SELECT boundary_id, geom
    FROM geologic_boundaries.boundaries
    WHERE boundary_id = ANY($1)
  `, [ req.query.boundary_id ], (error, result) => {
    if (error || !result) {
      return larkin.error(req, res, next)
    }

    dbgeo.parse(result.rows, {
      outputFormat: 'geojson',
      precision: 4
    }, (error, result) => {
      if (error) {
        return larkin.error(req, res, next)
      }

      larkin.sendData(req, res, next, {
        format: 'json',
        bare: true,
        compact: true
      }, {
        data: result
      })
    })
  })

}
