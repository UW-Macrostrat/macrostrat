const fs = require('fs')
const mapnik = require('tilestrata-mapnik')
const mbtiles = require('@mapbox/mbtiles')

module.exports = (options) => {
  let mapnikProvider = null
  let mbtilesProvider = null

  let blankRasterTile = ''

  fs.readFile(`${__dirname}/resources/tile.png`, (error, buffer) => {
    blankRasterTile = buffer
  })

  return {
    name: 'mapnik',
    init: (server, callback) => {
      // Create the provider
      mapnikProvider = new mapnik({
        pathname: `./seeder/etc/burwell_large_emphasized.xml`,
        tileSize: 512,
        scale: 2,
      })
      mapnikProvider.init(server, (error) => {
        if (error) {
          console.log('Error initializing mapnik provider', error)
        }
      })
      let path = `${__dirname}/seeder/carto-raster.mbtiles`
      let sinkUri = `mbtiles:///${path}`
      new mbtiles(sinkUri, (err, mbtileHandler) => {
        if (error) {
          console.log('Could not find carto-raster.mbtiles')
        }
        mbtilesProvider = provider
        callback()
      })
    },
    serve: (server, tile, callback) => {
      let z = parseInt(tile.z)

      // Mapnik
      if (z > 10) {
        mapnikProvider.serve(server, tile, (error, buffer) => {
          callback(error, buffer, {
            'Content-Type': 'image/png'
          })
        })
      }
      // mbtiles
      else {
        mbtilesProvider.getTile(tile.z, tile.x, tile.y, (error, buffer, headers) => {
          if (error || !buffer) {
            buffer = blankRasterTile
          }
          callback(null, buffer, {
            'Content-Type': 'image/png'
          })
        })
      }
    },
    destroy: (server, callback) => {
      callback()
    }
  }
}
