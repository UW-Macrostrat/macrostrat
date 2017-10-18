const tilestrata = require('tilestrata')
const mapnik = require('tilestrata-mapnik')
const vtile = require('tilestrata-vtile')
const vtileraster = require('tilestrata-vtile-raster')
const etag = require('tilestrata-etag')
const cartoProvider = require('./cartoProvider')
const redisCache = require('./redisCache')
const logger = require('./logger')

const MAX_ZOOM = 16
module.exports = tilestrata.middleware({
  server: (function() {
    var strata = tilestrata()

    // Carto
    strata.layer('carto')
      .route('*.mvt', {
        maxZoom: MAX_ZOOM
      })
        .use(cartoProvider())
        .use(redisCache({
            dir: `${__dirname}/tilecache/carto/vector`,
            defaultTile: `${__dirname}/resources/tile.mvt`
          }))
        .use(etag())

      .route('*.png', {
        maxZoom: MAX_ZOOM
      })
    //
        .use(vtileraster({
          xml: `${__dirname}/mapnik/burwell_vector_to_raster.xml`,
          tileSize: 512,
          scale: 1
        }, {
          tilesource: ['carto', '*.mvt']
        }))
        .use(redisCache({
          dir: `${__dirname}/tilecache/carto/raster`,
          defaultTile: `${__dirname}/resources/tile.png`
        }))
        .use(etag())
        .use(logger())

    // Tiny
    strata.layer('tiny', {
      maxZoom: MAX_ZOOM
    })
      .route('*.mvt')
        .use(vtile({
          xml: `${__dirname}/mapnik/tiny.xml`,
          tileSize: 512,
          scale: 1
        }))
        .use(redisCache({
          dir: `${__dirname}/tilecache/tiny/vector`,
          defaultTile: `${__dirname}/resources/tile.mvt`
        }))
        .use(etag())
      .route('*.png', {
        maxZoom: MAX_ZOOM
      })
        .use(vtileraster({
          xml: `${__dirname}/mapnik/burwell_vector_to_raster.xml`,
          tileSize: 512,
          scale: 2
        }, {
          tilesource: ['tiny', '*.mvt']
        }))
        .use(redisCache({
          dir: `${__dirname}/tilecache/tiny/raster`,
          defaultTile: `${__dirname}/resources/tile.png`
        }))
        .use(etag())


    // Small
    strata.layer('small', {
      maxZoom: MAX_ZOOM
    })
      .route('*.mvt')
        .use(vtile({
          xml: `${__dirname}/mapnik/small.xml`,
          tileSize: 512,
          scale: 1
        }))
        .use(redisCache({
          dir: `${__dirname}/tilecache/small/vector`,
          defaultTile: `${__dirname}/resources/tile.mvt`
        }))
        .use(etag())
      .route('*.png', {
        maxZoom: MAX_ZOOM
      })
        .use(vtileraster({
          xml: `${__dirname}/mapnik/burwell_vector_to_raster.xml`,
          tileSize: 512,
          scale: 2
        }, {
          tilesource: ['small', '*.mvt']
        }))
        .use(redisCache({
          dir: `${__dirname}/tilecache/small/raster`,
          defaultTile: `${__dirname}/resources/tile.png`
        }))
        .use(etag())


    // Medium
    strata.layer('medium', {
      maxZoom: MAX_ZOOM
    })
      .route('*.mvt')
        .use(vtile({
          xml: `${__dirname}/mapnik/medium.xml`,
          tileSize: 512,
          scale: 1
        }))
        .use(redisCache({
          dir: `${__dirname}/tilecache/medium/vector`,
          defaultTile: `${__dirname}/resources/tile.mvt`
        }))
        .use(etag())
      .route('*.png', {
        maxZoom: MAX_ZOOM
      })
        .use(vtileraster({
          xml: `${__dirname}/mapnik/burwell_vector_to_raster.xml`,
          tileSize: 512,
          scale: 2
        }, {
          tilesource: ['medium', '*.mvt']
        }))
        .use(redisCache({
          dir: `${__dirname}/tilecache/medium/raster`,
          defaultTile: `${__dirname}/resources/tile.png`
        }))
        .use(etag())


    // Large
    strata.layer('large', {
      maxZoom: MAX_ZOOM
    })
      .route('*.mvt')
        .use(vtile({
          xml: `${__dirname}/mapnik/large.xml`,
          tileSize: 512,
          scale: 1
        }))
        .use(redisCache({
          dir: `${__dirname}/tilecache/large/vector`,
          defaultTile: `${__dirname}/resources/tile.mvt`
        }))
        .use(etag())
      .route('*.png', {
        maxZoom: MAX_ZOOM
      })
        .use(vtileraster({
          xml: `${__dirname}/mapnik/burwell_vector_to_raster.xml`,
          tileSize: 512,
          scale: 2
        }, {
          tilesource: ['large', '*.mvt']
        }))
        .use(redisCache({
          dir: `${__dirname}/tilecache/large/raster`,
          defaultTile: `${__dirname}/resources/tile.png`
        }))
        .use(etag())

    return strata

  }())
})
