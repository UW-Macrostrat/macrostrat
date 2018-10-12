const pgHelper = require('@macrostrat/pg-helper')
const credentials = require('./credentials')

let pg = new pgHelper({
  host: credentials.pg_host,
  user: credentials.pg_user,
  port: credentials.pg_port,
  database: 'burwell'
})

const larkin = require('./larkin')

const scaleMap = {
  0: 7,
  1: 7,
  2: 7,
  3: 8,
  4: 9,
  5: 9,
  6: 11,
  7: 12,
  8: 12,
  9: 12,
  10: 12
}

// Requires a zoom, min_lng, min_lat, max_lng, max_lat
module.exports = (req, res, next) => {
  if (!req.query.zoom) {
    return larkin.error(req, res, next, 'A zoom paramter is required', 400)
  }
  if (!req.query.min_lng) {
    return larkin.error(req, res, next, 'A minimum longitude is required', 400)
  }
  if (!req.query.min_lat) {
    return larkin.error(req, res, next, 'A minimum latitude is required', 400)
  }
  if (!req.query.max_lng) {
    return larkin.error(req, res, next, 'A maxiumum longitude is required', 400)
  }
  if (!req.query.max_lat) {
    return larkin.error(req, res, next, 'A maximum latitude is required', 400)
  }
  larkin.queryPg('burwell', `
    SELECT hexgrids.hex_id, count(collection_no)
    FROM hexgrids.hexgrids
    JOIN hexgrids.pbdb_index ON pbdb_index.hex_id = hexgrids.hex_id
    WHERE ST_Intersects(geom, ST_SetSRID(ST_MakeEnvelope($1, $2, $3, $4), 4326))
      AND res = $5
    GROUP BY hexgrids.hex_id
  `, [
    parseFloat(req.query.min_lng),
    parseFloat(req.query.min_lat),
    parseFloat(req.query.max_lng),
    parseFloat(req.query.max_lat),
    scaleMap[parseInt(req.query.zoom)]
  ], (error, result) => {
    if (error) {
      return larkin.error(req, res, next, 'Something went wrong', 500)
    }
    larkin.sendData(req, res, next, {
      format: 'json',
      compact: true
    }, {
      data: result.rows
    })
  })
}
