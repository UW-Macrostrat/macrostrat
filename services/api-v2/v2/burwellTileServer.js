const tilestrata = require('tilestrata')
const http = require('http')

const passThrough = {
  init: (server, callback) => {
    callback()
  },
  reqhook: (server, tile, req, res, callback) => {
    http.get(`http://localhost:5555/carto/${tile.z}/${tile.x}/${tile.y}.png`, (response) => {
      let headers = response.headers
      res.set({
        'Content-Type': 'image/png',
        'content-length': headers['content-length'],
        'access-control-allow-origin': '*',
        'Cache-Control': headers['cache-control'],
        'etag': headers['etag'],
        'expires': headers['expires'],
        'strict-transport-security': headers['strict-transport-security'],
        'X-Powered-By': 'Tilestrata'
      })
      response.pipe(res)
    })
  }

}

module.exports = tilestrata.middleware({
  prefix: '/maps/burwell',
  server: (function() {
    var strata = tilestrata();

    strata.layer('emphasized')
      .route('tile.png')
      .use(passThrough)

    return strata

  }())
})
