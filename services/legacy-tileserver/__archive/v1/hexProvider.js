const fs = require('fs')
const mbtiles = require('@mapbox/mbtiles')

module.exports = (options) => {
  let mbtilesProvider = null

  let blankVectorTile = ''
  fs.readFile(`../resources/tile.mvt`, (error, buffer) => {
    blankVectorTile = buffer
  })

  return {
    name: 'hexgrid',
    init: (server, callback) => {
      new mbtiles(`./seeder/hexgrids.mbtiles`, (error, provider) => {
        if (error) {
          console.log('Could not find hexgrids.mbtiles')
        }
        mbtilesProvider = provider
        callback()
      })
    },
    serve: (server, tile, callback) => {
      mbtilesProvider.getTile(tile.z, tile.x, tile.y, (error, buffer, headers) => {
        if (error || !buffer) {
          buffer = blankVectorTile
        }
        callback(error, buffer, {
          'Content-Type': 'application/x-protobuf',
          'Content-Encoding': 'gzip'
        })
      })
    },
    destroy: (server, callback) => {
      callback()
    }
  }
}
