const tilestrata = require('tilestrata')

const tilePassThrough = {
  init: (server, callback) => {
    callback()
  },
  reqhook: (server, tile, req, res, callback) => {
    return res.redirect(301, `https://devtiles.macrostrat.org/carto/${tile.z}/${tile.x}/${tile.y}.png`)
  }
}

module.exports = tilestrata.middleware({
  prefix: '/maps/burwell',
  server: (() => {
    var strata = tilestrata();

    strata.layer('emphasized')
      .route('tile.png')
      .use(tilePassThrough)

    return strata;

  }())
})
