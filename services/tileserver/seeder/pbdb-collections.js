const vtile = require('tilestrata-vtile')
const fs = require('fs')
const mbtiles = require('@mapbox/mbtiles')
const zlib = require('zlib')
const config = require('../config')
const SphericalMercator = require('@mapbox/sphericalmercator')
const pgHelper = require('@macrostrat/pg-helper')
const credentials = require('../credentials')

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
  1: 3,
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
  let blankVectorTile = ''
  fs.readFile(`../resources/tile.mvt`, (error, buffer) => {
    blankVectorTile = buffer
  })
  let mbtileWriter = null

  return {
    name: 'pbdb-collections',
    init: (server, callback) => {
      // Initialize a tile provider for each scale
      config.scales.forEach(scale => {
        // Load the mbtile writer
        let sinkUri = `mbtiles://${__dirname}/pbdb-collections.mbtiles`
        new mbtiles(sinkUri, (err, mbtileHandler) => {
          mbtileWriter = mbtileHandler
        })
      })
      callback()
    },
    serve: (server, tile, callback) => {
      let z = parseInt(tile.z)
      if (z < 10) {

      }
      let extent = converter.bbox(tile.x, tile.y, z, false, 'WGS84')

      pg.query(`
        SELECT ST_AsMVT(q, 'pbdb-collections', 4096, 'geom') AS vtile
        FROM (
          SELECT
              cid,
              array_length(array_agg(collection_no), 1) AS n_collections,
              ST_AsMVTGeom(
                ST_ClosestPoint(ST_Collect(geom), ST_Centroid(ST_Collect(geom))),
                ST_SetSRID(ST_MakeBox2D(ST_MakePoint(${extent[0]}, ${extent[1]}), ST_MakePoint(${extent[2]}, ${extent[3]})), 4326),
                4096,
                512
              ) AS geom
          FROM (
            SELECT
              collection_no,
              name,
              ST_ClusterDBScan(geom, eps := ${zoomSimplification[z]}, minpoints := 2) over () AS cid,
              geom
            FROM macrostrat.pbdb_collections
            WHERE geom && ST_SetSRID(ST_MakeBox2D(ST_MakePoint($1, $2), ST_MakePoint($3, $4)), 4326)
           ) sub
          GROUP BY cid
        ) q
      `, extent, (error, result) => {
        if (error) {
          console.log(error)
        }
        let buffer = (error || !result || !result.length || !result[0].vtile) ? blankVectorTile : result[0].vtile

        mbtileWriter.startWriting(error => {
          mbtileWriter.putTile(tile.z, tile.x, tile.y, buffer, (error) => {
            if (error) {
              console.log(error)
            }
            mbtileWriter.stopWriting(error => {
              // don't return anything
              callback(null, blankVectorTile)
            })
          })
        })
      })
    },
    destroy: (server, callback) => {
      callback()
    }
  }
}
