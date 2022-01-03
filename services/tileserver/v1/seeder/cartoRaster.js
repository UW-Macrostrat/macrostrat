const mapnik = require('tilestrata-mapnik')
const fs = require('fs')
const mbtiles = require('@mapbox/mbtiles')
const config = require('../config')
const redis = require('redis')
const client = redis.createClient(6379, '127.0.0.1', {'return_buffers': true})

const scaleMap = {
  'tiny': [0, 1, 2, 3],
  'small': [4, 5],
  'medium': [6, 7, 8, 9],
  'large': [10, 11, 12, 13]
}

function makeKey(req) {
  return `${req.z},${req.x},${req.y},${req.layer},${req.filename}`
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
          pathname: `./etc/burwell_${scale}_emphasized.xml`,
          tileSize: 512,
          scale: 2,
        })
        // Initialize it
        providers[scale].init(server, (error) => {
          if (error) {
            console.log('Error initializing provider - ', error)
          }
        })

        // Load the mbtile writer
        let path = `${__dirname}/carto-raster.mbtiles`
        let sinkUri = `${path}?mode=rwc`
        new mbtiles(sinkUri, (err, mbtileHandler) => {
          if (err) {
            console.log(err)
          }
          mbtileWriter = mbtileHandler
        })
      })
      callback()
    },
    serve: (server, tile, callback) => {
      // Figure out which scale this zoom level belongs to
      let scale = zoomMap[tile.z] || 'large'
      providers[scale].serve(server, tile, (error, buffer) => {
        if (error) {
          console.log(error)
        }
        // Write the tile to Redis
        client.set(makeKey({
          x: tile.x,
          y: tile.y,
          z: tile.z,
          layer: 'carto',
          filename: 't.png'
        }), buffer)

        // stuff it in mbtiles
        mbtileWriter.startWriting(error => {
          if (error) {
            console.log('error - ', error)
          }
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
