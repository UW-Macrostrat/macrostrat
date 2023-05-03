const vtile = require('tilestrata-vtile')
const fs = require('fs')

const SphericalMercator = require('@mapbox/sphericalmercator')
const pgHelper = require('@macrostrat/pg-helper')
const credentials = require('./credentials')

let pg = new pgHelper({
  host: credentials.pg_host,
  user: credentials.pg_user,
  port: credentials.pg_port,
  database: 'burwell'
})

let converter = new SphericalMercator({
  size: 512
})

module.exports = (options) => {
  let blankVectorTile = ''
  fs.readFile(`../resources/tile.mvt`, (error, buffer) => {
    blankVectorTile = buffer
  })

  let scaleMap = {
    0: 'r7',
    1: 'r7',
    2: 'r7',
    3: 'r8',
    4: 'r9',
    5: 'r10',
    6: 'r11',
    7: 'r12',
    8: 'r12',
    9: 'r12',
    10: 'r12',
  }
  return {
    name: 'hex-grids',
    init: (server, callback) => {
      callback()
    },
    serve: (server, tile, callback) => {
      let reqParams = {}
      if (tile.qs) {
        tile.qs
          .split('&')
          .map(d => { return d.split('=') })
          .forEach(d => { reqParams[d[0]] = d[1] })
      }

      let where = []
      let params = []

      if (reqParams.b_age) {
        where.push(`pb.early_age <= $${where.length + 1}`)
        params.push(parseFloat(reqParams.b_age))
      }
      if (reqParams.t_age) {
        where.push(`pb.late_age >= $${where.length + 1}`)
        params.push(parseFloat(reqParams.t_age))
      }

      where = where.join(' AND ')

      if (where.length) {
        where = ' AND ' + where
      }

      let z = parseInt(tile.z)
      let extent = converter.bbox(tile.x, tile.y, z, false, '900913')
      let table = scaleMap[z] || 'r12'

      pg.query(`
        SELECT ST_AsMVT(q, 'hex-grids', 4096, 'geom') AS vtile
        FROM (
          SELECT
            hex_id,
            count(h.collection_no) AS n_collections,
            ST_AsMVTGeom(
              ST_Transform(ST_SetSRID(r.geom, 4326), 3857),
              ST_MakeEnvelope(${extent[0]}, ${extent[1]}, ${extent[2]}, ${extent[3]}, 3857),
              4096,
              512
            ) AS geom
          FROM hexgrids."${table}" r
          JOIN carto_new.pbdb_hex_index h ON h.${table} = r.hex_id
          JOIN macrostrat.pbdb_collections pb ON pb.collection_no = h.collection_no
          WHERE ST_Transform(r.geom, 3857) && ST_MakeEnvelope(${extent[0]}, ${extent[1]}, ${extent[2]}, ${extent[3]}, 3857)
          ${where}
          GROUP BY hex_id
        ) q
      `, params, (error, result) => {
        let buffer = (error || !result || !result.length || !result[0].vtile) ? blankVectorTile : result[0].vtile

        callback(error, buffer, {
          'Content-Type': 'application/x-protobuf'
        })
      })
    },
    destroy: (server, callback) => {
      callback()
    }
  }
}
