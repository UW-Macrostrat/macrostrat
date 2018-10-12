const larkin = require('./larkin')

const scaleMap = {
  0: 7,
  1: 7,
  2: 7,
  3: 8,
  4: 9,
  5: 9,
  6: 10,
  7: 11,
  8: 11,
  9: 12,
  10: 12
}

// Requires a zoom, min_lng, min_lat, max_lng, max_lat
module.exports = (req, res, next) => {
  if (!req.params.zoom) {
    return larkin.error(req, res, next, 'A zoom paramter is required', 400)
  }
  larkin.queryPg('burwell', `
    SELECT max(count) AS max FROM (
      SELECT hexgrids.hex_id, count(collection_no) AS count
      FROM hexgrids.hexgrids
      JOIN hexgrids.pbdb_index ON pbdb_index.hex_id = hexgrids.hex_id
      WHERE res = $1
      GROUP BY hexgrids.hex_id
    ) sub
  `, [
    scaleMap[parseInt(req.params.zoom)]
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
