const tilestrata = require('tilestrata')
const cartoRaster = require('./cartoRaster')
const cartoVector = require('./cartoVector')

module.exports = tilestrata.middleware({
  server: (function() {
    let strata = tilestrata()

    // carto mvt and png
    strata.layer('carto')
      // .route('*.mvt')
      //   .use(cartoVector())
      .route('*.png')
        .use(cartoRaster())

    // carto slim mvt
    // strata.layer('carto-slim')
    //   .route('*.mvt')
    //     .use(vtileMaker)

    return strata

  }())
})
