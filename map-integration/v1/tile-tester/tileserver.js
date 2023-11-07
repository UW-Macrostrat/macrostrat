var tilestrata = require("tilestrata")
var mapnik = require("tilestrata-mapnik")
var vtile = require("tilestrata-vtile")
var etag = require("tilestrata-etag")
//var vtile = require("tilestrata-vtile")
var yaml = require('yamljs')
var credentials = yaml.load('../credentials.yml')

module.exports = tilestrata.middleware({
  prefix: '/tiles',
  server: (function() {
    var strata = tilestrata()
    var layers = ['emphasized']
    // Create a provider for all active tile layers
    layers.forEach(function(layer) {
      ['tiny', 'small', 'medium', 'large'].forEach(function(scale) {
        strata.layer(`${layer}_${scale}`)
            .route('tile.png')
              .use(mapnik({
                  pathname: `../tiles/compiled_styles/burwell_${scale}_${layer}.xml`,
                  tileSize: 512,
                  scale: 2
              }))
              .use(etag())
            // .route('tile.pbf')
            //   .use(vtile({
            //       xml: `../tiles/compiled_styles/burwell_vector_${scale}_${layer}.xml`,
            //       tileSize: 256,
            //       metatile: 1,
            //       bufferSize: 128
            //   }))
            //   .use(etag())
      })
    })
    var scales = ['tiny', 'small', 'medium', 'large']

    scales.forEach(function(scale) {
      strata.layer(`${scale}`)
          .route('tile.pbf')
            .use(vtile({
                xml: `../tiles/compiled_styles/burwell_vector_${scale}.xml`,
                tileSize: 256,
                metatile: 1,
                bufferSize: 128
            }))
            .use(etag())
    })



    return strata;

  }())
})
