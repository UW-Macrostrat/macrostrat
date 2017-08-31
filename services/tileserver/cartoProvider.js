const vtile = require('tilestrata-vtile')
const config = require('./config')

module.exports = (options) => {
  // Create a hash for looking up the proper scale for each zoom level
  let zoomMap = {}
  Object.keys(config.scaleMap).forEach(scale => {
    config.scaleMap[scale].forEach(z => {
      zoomMap[z] = scale
    })
  })

  // We will create a vector tile provider for each map scale
  let providers = {}

  return {
    name: 'carto',
    init: (server, callback) => {
      // Initialize a tile provider for each scale
      config.scales.forEach(scale => {
        // Create the provider
        providers[scale] = new vtile({
          xml: `./mapnik/burwell_vector_${scale}.xml`,
        })
        // Initialize it
        providers[scale].init(server, (error) => {

        })
      })
      callback()
    },
    serve: (server, tile, callback) => {
      // Figure out which scale this zoom level belongs to
      let scale = zoomMap[tile.z] || 'large'
      providers[scale].serve(server, tile, (error, buffer) => {
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
