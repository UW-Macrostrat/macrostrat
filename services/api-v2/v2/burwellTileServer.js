const tilestrata = require('tilestrata')
const http = require('http')
const fs = require('fs')

const passThrough = {
  init: (server, callback) => {
    callback()
  },
  reqhook: (server, tile, req, res, callback) => {
    let options = {
      hostname: 'localhost',
      port: 5555,
      path: `/carto/${tile.z}/${tile.x}/${tile.y}.png${req._parsedUrl.search || ''}`,
      headers: {
        referer: req.headers.referer || ''
      },
    }

    let tileReq = http.get(options, (response) => {
      if (!response) {
        fs.readFile(__dirname + '/default@2x.png', (error, buffer) => {
          res.set('Content-Type', 'image/png')
          res.end(buffer)
        })
      }

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

    tileReq.on('error', (error) => {
      fs.readFile(__dirname + '/default@2x.png', (error, buffer) => {
        res.set('Content-Type', 'image/png')
        res.end(buffer)
      })
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
