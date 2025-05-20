const fs = require('fs')
const mapnik = require('tilestrata-vtile')
const mbtiles = require('@mapbox/mbtiles')

module.exports = (options) => {
  let mapnikProvider = null
  let mbtilesProvider = null

  let blankVectorTile = ''
  fs.readFile(`${__dirname}/resources/tile.mvt`, (error, buffer) => {
    blankVectorTile = buffer
  })

  return {
    name: 'carto-slim',
    init: (server, callback) => {
      // Create the a mapnik provider for dynamic tile creation
      mapnikProvider = new mapnik({
        xml: `./mapnik/burwell_vector_slim_large.xml`,
        tileSize: 512,
        scale: 2,
      })
      mapnikProvider.init(server, (error) => {
        if (error) {
          console.log('Error initializing mapnik provider', error)
        }
      })
      // Create a mbtiles provider for pre-created tile fetching
      new mbtiles(`./seeder/carto-slim.mbtiles`, (error, provider) => {
        if (error) {
          console.log('Could not find carto-slim-vector.mbtiles')
        }
        mbtilesProvider = provider
        callback()
      })
    },
    serve: (server, tile, callback) => {
      let z = parseInt(tile.z)

      // Mapnik
      if (z > 12) {
        mapnikProvider.serve(server, tile, (error, buffer) => {
          callback(error, buffer, {
            'Content-Type': 'application/x-protobuf',
            'Content-Encoding': 'gzip'
          })
        })
      }
      // mbtiles
      else {
        mbtilesProvider.getTile(tile.z, tile.x, tile.y, (error, buffer, headers) => {
          if (error || !buffer) {
            buffer = blankVectorTile
          }
          callback(null, buffer, {
            'Content-Type': 'application/x-protobuf',
            'Content-Encoding': 'gzip'
          })
        })
      }
    },
    destroy: (server, callback) => {
      callback()
    }
  }
}
