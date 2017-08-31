'use strict'

const tilestrata = require('tilestrata')
const mapnik = require('tilestrata-mapnik')
const vtile = require('tilestrata-vtile')
const vtileraster = require('tilestrata-vtile-raster')
const etag = require('tilestrata-etag')
const cartoProvider = require('./cartoProvider')
const redisCache = require('./redisCache')

module.exports = tilestrata.middleware({
  prefix: '/tiles',
  server: (function() {
    var strata = tilestrata()

    // Carto
    strata.layer('carto')
      .route('tile.mvt')
        .use(cartoProvider())
        .use(redisCache({
            dir: `${__dirname}/tilecache/carto/vector`,
            defaultTile: __dirname + "/default@2x.png"
          }))
        .use(etag())
      .route('tile.png')
        .use(vtileraster({
          xml: `../tiles/compiled_styles/burwell_vector_to_raster.xml`,
          tileSize: 512,
          scale: 1
        }, {
          tilesource: ['carto', 'tile.mvt']
        }))
        .use(redisCache({
          dir: `${__dirname}/tilecache/carto/raster`,
          defaultTile: __dirname + "/default@2x.png"
        }))
        .use(etag())

    // Tiny
    strata.layer('tiny')
      .route('tile.mvt')
        .use(vtile({
          xml: './mapnik/tiny.xml',
          tileSize: 512,
          scale: 1
        }))
        .use(redisCache({
          dir: `${__dirname}/tilecache/tiny/vector`,
          defaultTile: __dirname + "/default@2x.png"
        }))
        .use(etag())
      .route('tile.png')
        .use(vtileraster({
          xml: `../tiles/compiled_styles/burwell_vector_to_raster.xml`,
          tileSize: 512,
          scale: 2
        }, {
          tilesource: ['tiny', 'tile.mvt']
        }))
        .use(redisCache({
          dir: `${__dirname}/tilecache/tiny/raster`,
          defaultTile: __dirname + "/default@2x.png"
        }))
        .use(etag())

    // Small
    strata.layer('small')
      .route('tile.mvt')
        .use(vtile({
          xml: './mapnik/small.xml',
          tileSize: 512,
          scale: 1
        }))
        .use(redisCache({
          dir: `${__dirname}/tilecache/small/vector`,
          defaultTile: __dirname + "/default@2x.png"
        }))
        .use(etag())
      .route('tile.png')
        .use(vtileraster({
          xml: `../tiles/compiled_styles/burwell_vector_to_raster.xml`,
          tileSize: 512,
          scale: 2
        }, {
          tilesource: ['small', 'tile.mvt']
        }))
        .use(etag())

    // Medium
    strata.layer('medium')
      .route('tile.mvt')
        .use(vtile({
          xml: './mapnik/medium.xml',
          tileSize: 512,
          scale: 1
        }))
        .use(redisCache({
          dir: `${__dirname}/tilecache/medium/vector`,
          defaultTile: __dirname + "/default@2x.png"
        }))
        .use(etag())
      .route('tile.png')
        .use(vtileraster({
          xml: `../tiles/compiled_styles/burwell_vector_to_raster.xml`,
          tileSize: 512,
          scale: 2
        }, {
          tilesource: ['medium', 'tile.mvt']
        }))
        .use(etag())

    // Large
    strata.layer('large')
      .route('tile.mvt')
        .use(vtile({
          xml: './mapnik/large.xml',
          tileSize: 512,
          scale: 1
        }))
        .use(redisCache({
          dir: `${__dirname}/tilecache/large/vector`,
          defaultTile: __dirname + "/default@2x.png"
        }))
        .use(etag())
      .route('tile.png')
        .use(vtileraster({
          xml: `../tiles/compiled_styles/burwell_vector_to_raster.xml`,
          tileSize: 512,
          scale: 2
        }, {
          tilesource: ['large', 'tile.mvt']
        }))
        .use(etag())

    return strata

  }())
})
