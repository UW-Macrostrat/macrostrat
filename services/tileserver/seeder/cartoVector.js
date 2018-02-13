const vtile = require('tilestrata-vtile')
const fs = require('fs')
const mbtiles = require('@mapbox/mbtiles')
const zlib = require('zlib')
const config = require('../config')

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
        let sinkUri = 'mbtiles:///Users/john/code/macrostrat/tileserver/carto-vector.mbtiles'
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
        mbtileWriter.startWriting(error => {
          zlib.gzip(buffer, (error, gzipped) => {
            mbtileWriter.putTile(tile.z, tile.x, tile.y, gzipped, (error) => {
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
      })
    },
    destroy: (server, callback) => {
      callback()
    }
  }
}
