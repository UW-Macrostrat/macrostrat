var tilestrata = require("tilestrata")
var mapnik = require("tilestrata-mapnik")
var etag = require("tilestrata-etag")
//var vtile = require("tilestrata-vtile")
var yaml = require('yamljs')
var credentials = yaml.load('../credentials.yml')

module.exports = tilestrata.middleware({
  prefix: '/tiles',
  server: (function() {
    var strata = tilestrata()

    // Create a provider for all active tile layers
    ['emphasized'].forEach(function(layer) {
      ['tiny', 'small', 'medium', 'large'].forEach(function(scale) {
        strata.layer(`${layer}_${scale}`)
            .route('tile.png')
            .use(mapnik({
                pathname: `../tiles/compiled_styles/burwell_${scale}_${layer}.xml`,
                tileSize: 512,
                scale: 2
            }))
            .use(etag())
      })
    })

    // strata.layer('vector')
    //     .route('tile.pbf')
    //         .use(vtile({
    //             xml: __dirname + '/burwell_vtile_tiny.xml',
    //             tileSize: 256,
    //             metatile: 1,
    //             bufferSize: 128
    //         }))
    //         .use(etag())


    return strata;

  }())
})
