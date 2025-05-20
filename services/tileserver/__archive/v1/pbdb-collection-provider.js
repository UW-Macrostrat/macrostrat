const fs = require('fs')
const mbtiles = require('@mapbox/mbtiles')
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

const zoomSimplification = {
  1: 5,
  2: 0.6,
  3: 0.4,
  4: 0.35,
  5: 0.2,
  6: 0.1,
  7: 0.05,
  8: 0.02,
  9: 0.01,
  10: 0,
  11: 0,
  12: 0
}

module.exports = (options) => {
  let mbtilesProvider = null
  let blankVectorTile = ''
  fs.readFile(`${__dirname}/resources/tile.mvt`, (error, buffer) => {
    blankVectorTile = buffer
  })

  return {
    name: 'pbdb-collections-provider',
    init: (server, callback) => {
      new mbtiles(`./seeder/pbdb-collections.mbtiles`, (error, provider) => {
        if (error) {
          console.log('Could not find carto-slim-vector.mbtiles')
        }
        mbtilesProvider = provider
        callback()
      })
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

      if (z < 10) {
        mbtilesProvider.getTile(tile.z, tile.x, tile.y, (error, buffer, headers) => {
          if (error || !buffer) {
            buffer = blankVectorTile
          }
          callback(null, buffer, {
            'Content-Type': 'application/x-protobuf'
          })
        })
      } else {

        let extent = converter.bbox(tile.x, tile.y, z, false, '900913')

        // Web mercator doesn't operate outside of -85 to 85, so verify we are getting good coords
        // extent[0] = (extent[0] < -85) ? -85 : extent[0]
        // extent[2] = (extent[2] > 85) ? 85 : extent[2]

        pg.query(`
          SELECT ST_AsMVT(q, 'pbdb-collections', 4096, 'geom') AS vtile
          FROM (
            SELECT
              collection_no,
              ST_AsMVTGeom(
                ST_Transform(ST_SetSRID(geom, 4326), 3857),
                ST_MakeEnvelope(${extent[0]}, ${extent[1]}, ${extent[2]}, ${extent[3]}, 3857),
                4096,
                512
              ) AS geom
            FROM macrostrat.pbdb_collections
            WHERE ST_Transform(geom, 3857) && ST_MakeEnvelope(${extent[0]}, ${extent[1]}, ${extent[2]}, ${extent[3]}, 3857)
          ) q
        `, [], (error, result) => {
          if (error || !result || !result.length || !result[0].vtile) {
            return callback(error, blankVectorTile, {
              'Content-Type': 'application/x-protobuf'
            })
          }
          callback(error, result[0].vtile, {
            'Content-Type': 'application/x-protobuf'
          })
        })
      }
    },
    destroy: (server, callback) => {
      callback()
    }
  }
}
