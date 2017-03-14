var larkin = require('./larkin')
var api = require('./api')
var dbgeo = require('dbgeo')


module.exports = function(req, res, next, callback) {
  var where = []
  var params = []
  var limit = ('sample' in req.query) ? 'LIMIT 5' : ''


  if (req.query.wof_id) {
    where.push(`a.wof_id = ANY(\$${where.length + 1})`)
    params.push(larkin.parseMultipleIds(req.query.wof_id))
  }
  if (req.query.placetype) {
    where.push(`a.placetype = ANY(\$${where.length + 1})`)
    params.push(larkin.parseMultipleStrings(req.query.placetype))
  }
  if (req.query.name) {
    where.push(`a.name = ANY(\$${where.length + 1})`)
    params.push(larkin.parseMultipleStrings(req.query.name))
  }
  if (req.query.name_like) {
    where.push(`a.name = \$${where.length + 1}`)
    params.push(`%${req.query.placetype}%`)
  }

  if (!where.length && !('sample' in req.query)) {
    return larkin.error(req, res, next, 'Please provide at least one valid parameter', 400)
  }


  larkin.queryPg('wof', `
    SELECT
      a.wof_id,
      a.placetype,
      a.name,
      COALESCE(a.name_formal, '') AS name_formal,
      (SELECT row_to_json(_) FROM (SELECT cnt.wof_id, cnt.name) _) AS continent,
      (SELECT row_to_json(_) FROM (SELECT cntry.wof_id, cntry.name, cntry.iso2, cntry.iso3) _) AS country,
      (SELECT row_to_json(_) FROM (SELECT r.wof_id, r.name) _) AS region,
      (SELECT row_to_json(_) FROM (SELECT c.wof_id, c.name) _) AS county,
      (SELECT row_to_json(_) FROM (SELECT l.wof_id, l.name) _) AS locality,
      hstore_to_json(a.other_names) AS other_names
      ${req.query.format && api.acceptedFormats.geo[req.query.format] ? ', a.geom' : ''}
    FROM places a
    LEFT JOIN places l ON l.wof_id = a.locality
    LEFT JOIN places c ON c.wof_id = a.county
    LEFT JOIN places r ON r.wof_id = a.region
    LEFT JOIN places cntry ON cntry.wof_id = a.country
    LEFT JOIN places cnt ON cnt.wof_id = a.continent
    WHERE ${where.join(' AND ')}
    ${limit}
  `, params, function(error, result) {
    if (error) {
      return larkin.error(req, res, next, 'Internal error', 500)
    }
    // if a geographic format is requested
    if (req.query.format && api.acceptedFormats.geo[req.query.format]) {
      dbgeo.parse(result.rows, {
        'outputFormat': larkin.getOutputFormat(req.query.format),
        'precision': 6
      }, function(error, result) {
        if (error) {
          return larkin.error(req, res, next, 'Internal error', 500)
        }
        larkin.sendData(req, res, next, {
          format: (api.acceptedFormats.standard[req.query.format]) ? req.query.format : 'json',
          bare: (api.acceptedFormats.bare[req.query.format]) ? true : false
        }, {
          data: result
        })
      })
    } else {
      larkin.sendData(req, res, next, {
        format: (api.acceptedFormats.standard[req.query.format]) ? req.query.format : 'json',
        bare: (api.acceptedFormats.bare[req.query.format]) ? true : false
      }, {
        data: result.rows
      })
    }
  })
}
