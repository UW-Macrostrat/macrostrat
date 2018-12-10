const tilestrata = require('tilestrata')
const cartoRaster = require('./cartoRaster')
// const hexgrid = require('./hexgrid')

module.exports = tilestrata.middleware({
  server: (function() {
    let strata = tilestrata()

    // carto mvt and png
    strata.layer('carto')
      .route('*.png')
        .use(cartoRaster())

    // strata.layer('hexgrid')
    //   .route("*.mvt")
    //     .use(hexgrid())

    return strata

  }())
})
