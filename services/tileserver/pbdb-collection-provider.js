const fs = require('fs')
const mbtiles = require('@mapbox/mbtiles')
const SphericalMercator = require('@mapbox/sphericalmercator')
const pgHelper = require('@macrostrat/pg-helper')
const credentials = require('./credentials')
const zlib = require('zlib')

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
      let z = parseInt(tile.z)
      let extent = converter.bbox(tile.x, tile.y, z, false, 'WGS84')

      if (z < 10) {
        mbtilesProvider.getTile(tile.z, tile.x, tile.y, (error, buffer, headers) => {
          if (error || !buffer) {
            buffer = blankVectorTile
          }
          callback(null, buffer, {
            'Content-Type': 'application/x-protobuf',
            'Content-Encoding': 'gzip'
          })
        })
      } else {
        pg.query(`
          SELECT ST_AsMVT(q, 'pbdb-collections', 4096, 'geom') AS vtile
          FROM (
            SELECT
              collection_no,
              ST_AsMVTGeom(
                geom,
                ST_SetSRID(ST_MakeBox2D(ST_MakePoint(${extent[0]}, ${extent[1]}), ST_MakePoint(${extent[2]}, ${extent[3]})), 4326),
                4096,
                512
              ) AS geom
            FROM macrostrat.pbdb_collections
            WHERE geom && ST_SetSRID(ST_MakeBox2D(ST_MakePoint($1, $2), ST_MakePoint($3, $4)), 4326)
          ) q
        `, extent, (error, result) => {
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
      // if (z >= 10) {
      //
      // } else {
      //   pg.query(`
      //     SELECT ST_AsMVT(q, 'pbdb-collections', 4096, 'geom') AS vtile
      //     FROM (
      //       SELECT
      //           cid,
      //           array_length(array_agg(collection_no), 1) AS n_collections,
      //           ST_AsMVTGeom(
      //             ST_Centroid(ST_Collect(geom)),
      //             ST_SetSRID(ST_MakeBox2D(ST_MakePoint(${extent[0]}, ${extent[1]}), ST_MakePoint(${extent[2]}, ${extent[3]})), 4326),
      //             4096,
      //             512
      //           ) AS geom
      //       FROM (
      //         SELECT
      //           collection_no,
      //           name,
      //           ST_ClusterDBScan(geom, eps := ${zoomSimplification[z]}, minpoints := 2) over () AS cid,
      //           geom
      //         FROM macrostrat.pbdb_collections
      //         WHERE geom && ST_SetSRID(ST_MakeBox2D(ST_MakePoint($1, $2), ST_MakePoint($3, $4)), 4326)
      //        ) sub
      //       GROUP BY cid
      //     ) q
      //   `, extent, (error, result) => {
      //     if (error || !result || !result.length || !result[0].vtile) {
      //       return callback(error, blankVectorTile, {
      //         'Content-Type': 'application/x-protobuf'
      //       })
      //     }
      //     callback(error, result[0].vtile, {
      //       'Content-Type': 'application/x-protobuf'
      //     })
      //   })
      // }
    },
    destroy: (server, callback) => {
      callback()
    }
  }
}
