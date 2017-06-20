'use strict'
const larkin = require('./larkin')
const api = require('./api')
const dbgeo = require('dbgeo')

const MAXRESULTS = 5000

module.exports = (req, res, next, callback) => {
  let where = []
  let params = []
  let limit = ('sample' in req.query) ? 'LIMIT 5' : ''

  if (req.query.wof_id) {
    if (req.query.childtype) {
      where.push(`a.wof_id IN (
        SELECT wof_id
        FROM places
        WHERE
          CASE
            WHEN (SELECT placetype FROM places WHERE wof_id = $1) = 'continent'
              THEN ( continent = $1 )
            WHEN (SELECT placetype FROM places WHERE wof_id = $1) = 'country'
              THEN ( country = $1 )
            WHEN (SELECT placetype FROM places WHERE wof_id = $1) = 'region'
              THEN ( region = $1 )
            WHEN (SELECT placetype FROM places WHERE wof_id = $1) = 'county'
              THEN ( county = $1 )
            WHEN (SELECT placetype FROM places WHERE wof_id = $1) = 'locality'
              THEN ( locality = $1 )
            ELSE ( wof_id = -9999 )
          END

          AND placetype = $2
      )`)
      params.push(req.query.wof_id, req.query.childtype)
    } else {
      where.push(`a.wof_id = ANY(\$${where.length + 1})`)
      params.push(larkin.parseMultipleIds(req.query.wof_id))
    }
  }
  if (req.query.placetype && !req.query.childtype) {
    where.push(`a.placetype = ANY(\$${where.length + 1})`)
    params.push(larkin.parseMultipleStrings(req.query.placetype))
  }
  if (req.query.name) {
    if (req.query.childtype) {
      if (!req.query.placetype) {
        return larkin.error(req, res, next, 'You must provide a "placetype" when querying for children with a "name"', 401)
      }

      where.push(`a.wof_id IN (
        SELECT wof_id
        FROM places
        WHERE
          CASE
            WHEN $2 = 'continent' AND $3 = 'country'
              THEN ( continent = ANY( SELECT wof_id  FROM places WHERE name = ANY($1) AND placetype = $2) )
            WHEN $2 = 'country' AND $3 = 'region'
              THEN ( country = ANY( SELECT wof_id  FROM places WHERE name = ANY($1) AND placetype = $2) )
            WHEN $2 = 'region' AND $3 = 'county'
              THEN ( region = ANY( SELECT wof_id  FROM places WHERE name = ANY($1) AND placetype = $2) )
            WHEN $2 = 'county' AND $3 = 'locality'
              THEN ( county = ANY( SELECT wof_id  FROM places WHERE name = ANY($1) AND placetype = $2) )
            WHEN $2 = 'locality' AND $3 = 'locality'
              THEN ( locality = ANY( SELECT wof_id  FROM places WHERE name = ANY($1) AND placetype = $2) )
            ELSE ( wof_id = -9999)
          END
          
          AND placetype = $3
      )`)
      params.push(larkin.parseMultipleStrings(req.query.name), req.query.placetype, req.query.childtype)
    } else {
      where.push(`a.name = ANY(\$${where.length + 1})`)
      params.push(larkin.parseMultipleStrings(req.query.name))
    }
  }
  if (req.query.name_like) {
    where.push(`a.name = \$${where.length + 1}`)
    params.push(`%${req.query.placetype}%`)
  }
  if (req.query.lng && req.query.lat) {
    where.push(`ST_Intersects(a.geom, ST_SetSRID(ST_MakePoint(\$${where.length + 1}, \$${where.length + 2}), 4326))`)
    params.push(larkin.normalizeLng(req.query.lng), req.query.lat)
  }

  if (!where.length && !('sample' in req.query)) {
    return larkin.error(req, res, next, 'Please provide at least one valid parameter', 400)
  }

  larkin.queryPg('wof', `
    SELECT
      COUNT(*) AS n_rows
    FROM places a
    LEFT JOIN places l ON l.wof_id = a.locality
    LEFT JOIN places c ON c.wof_id = a.county
    LEFT JOIN places r ON r.wof_id = a.region
    LEFT JOIN places cntry ON cntry.wof_id = a.country
    LEFT JOIN places cnt ON cnt.wof_id = a.continent
    WHERE ${where.join(' AND ')}
    ${limit}
  `, params, (error, result) => {
    if (error || !result || !result.rows) {
      return larkin.error(req, res, next, 'Internal error', 500)
    }
    if (result.rows[0].n_rows > MAXRESULTS) {
      return larkin.error(req, res, next, 'Too many results returned by this query. Please refine your search and try again', 401)
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
    `, params, (error, result) => {
      if (error) {
        return larkin.error(req, res, next, 'Internal error', 500)
      }
      // if a geographic format is requested
      if (req.query.format && api.acceptedFormats.geo[req.query.format]) {
        dbgeo.parse(result.rows, {
          'outputFormat': larkin.getOutputFormat(req.query.format),
          'precision': 6
        }, (error, result) => {
          if (error) {
            return larkin.error(req, res, next, 'Internal error', 500)
          }
          larkin.sendData(req, res, next, {}, {
            data: result
          })
        })
      } else {
        larkin.sendData(req, res, next, {}, {
          data: result.rows
        })
      }
    })
  })
}
