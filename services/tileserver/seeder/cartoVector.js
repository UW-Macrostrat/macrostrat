const vtile = require('tilestrata-vtile')
const fs = require('fs')
const mbtiles = require('@mapbox/mbtiles')
const zlib = require('zlib')
const config = require('../config')
const redis = require('redis')
const client = redis.createClient(6379, '127.0.0.1', {'return_buffers': true})

function key(req) {
  return `${req.z},${req.x},${req.y},${req.layer},${req.filename}`
}


module.exports = (options) => {
  // Create a hash for looking up the proper scale for each zoom level
  let zoomMap = {}
  Object.keys(config.scaleMap).forEach(scale => {
    config.scaleMap[scale].forEach(z => {
      zoomMap[z] = scale
    })
  })

  let blankVectorTile = ''
  fs.readFile(`../resources/tile.mvt`, (error, buffer) => {
    blankVectorTile = buffer
  })

  // We will create a vector tile provider for each map scale
  let providers = {}
  let mbtileWriter = null

  return {
    name: 'carto',
    init: (server, callback) => {
      // Initialize a tile provider for each scale
      config.scales.forEach(scale => {
        // Create the provider
        providers[scale] = new vtile({
          xml: `../mapnik/burwell_vector_${scale}.xml`,
        })
        // Initialize it
        providers[scale].init(server, (error) => {})

        // Load the mbtile writer
        let path = `${__dirname}/carto.mbtiles`
        let sinkUri = `mbtiles:///${path}`
        new mbtiles(sinkUri, (err, mbtileHandler) => {
          mbtileWriter = mbtileHandler
        })
      })
      callback()
    },
    serve: (server, tile, callback) => {
      // Figure out which scale this zoom level belongs to
      let scale = zoomMap[tile.z] || 'large'
      providers[scale].serve(server, tile, (error, buffer) => {
        // stuff it in mbtiles
        if (!buffer) {
          return callback(null, blankVectorTile)
        }
        // Write the tile to Redis
        client.set(key({
          x: tile.x,
          y: tile.y,
          z: tile.z,
          layer: 'carto',
          filename: 't.mvt'
        }), buffer)

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
