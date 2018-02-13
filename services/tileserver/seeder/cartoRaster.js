const mapnik = require('tilestrata-mapnik')
const fs = require('fs')
const mbtiles = require('@mapbox/mbtiles')
const config = require('../config')

const scaleMap = {
  'tiny': [0, 1, 2, 3],
  'small': [4, 5],
  'medium': [6, 7, 8, 9],
  'large': [10, 11, 12, 13]
}

module.exports = (options) => {
  // Create a hash for looking up the proper scale for each zoom level
  let zoomMap = {}
  Object.keys(scaleMap).forEach(scale => {
    scaleMap[scale].forEach(z => {
      zoomMap[z] = scale
    })
  })

  // We will create a tile provider for each map scale
  let providers = {}
  let mbtileWriter = null

  let blankRasterTile = ''
  fs.readFile(`../resources/tile.png`, (error, buffer) => {
    blankRasterTile = buffer
  })

  return {
    name: 'cartoRaster',
    init: (server, callback) => {

      // Initialize a tile provider for each scale
      config.scales.forEach(scale => {
        // Create the provider
        providers[scale] = new mapnik({
          pathname: `../mapnik/burwell_${scale}_emphasized.xml`,
          tileSize: 512,
          scale: 2,
        })
        // Initialize it
        providers[scale].init(server, (error) => {})

        // Load the mbtile writer
        let path = `${__dirname}/carto-raster.mbtiles`
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
        mbtileWriter.startWriting(error => {
          mbtileWriter.putTile(tile.z, tile.x, tile.y, buffer, (error) => {
            if (error) {
              console.log(error)
            }
            mbtileWriter.stopWriting(error => {
              // don't return anything
              callback(null, blankRasterTile)
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
