const tilestrata = require('tilestrata')
const cartoRaster = require('./cartoRaster')
const cartoVector = require('./cartoVector')
const cartoSlimVector = require('./cartoSlimVector')
const pbdbCollections = require('./pbdb-collections')

module.exports = tilestrata.middleware({
  server: (function() {
    let strata = tilestrata()

    strata.layer('pbdb-collections')
      .route('*.mvt')
        .use(pbdbCollections())

    // carto mvt and png
    strata.layer('carto')
      .route('*.png')
        .use(cartoRaster())
      .route('*.mvt')
        .use(cartoVector())

    strata.layer('carto-slim')
      .route('*.mvt')
        .use(cartoSlimVector())

    return strata

  }())
})
