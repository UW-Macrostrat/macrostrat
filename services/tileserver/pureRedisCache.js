const redis = require('redis')
const client = redis.createClient(6379, '127.0.0.1', {'return_buffers': true})
const credentials = require('./credentials')

module.exports = (options) => {
    function key(req) {
      return `${req.z},${req.x},${req.y},${req.layer},${req.filename}`
    }

    function getHeaders(type) {
      if (type === 'raster') {
        return {
          'Content-Type': 'image/png',
        }
      } else {
        return {
          'Content-Type': 'application/x-protobuf',
          'Content-Encoding': 'gzip'
        }
      }
    }

    function deleteTile(tile) {
      client.del(key(tile), (error) => {
        // Let it fail. What do I care.
      })
    }

    return {
        init: (server, callback) => {
          callback()
        },

        get: (server, tile, callback) => {
          // Handle a cache-clear request
          if (tile.headers['X-Tilestrata-DeleteTile'] && tile.headers['X-Tilestrata-DeleteTile'] === credentials.secret) {
            deleteTile(tile)
            return callback(null, (tile.filename.indexOf('.png') > -1 ? blankRasterTile : blankVectorTile))
          }

          // Check if tile exists in memory
          client.get(key(tile), (error, data) => {
            // if yes, return it
            if (data) {
              let headers = (tile.filename.indexOf('.png') > -1) ? getHeaders('raster') : getHeaders('vector')
              headers['X-TileStrata-RedisHit'] = 1
              return callback(null, data, headers)
            }
            // Otherwise let the provider make a new tile and put it in Redis for next time
            callback(null)
          })
        },

        set: (server, req, buffer, headers, callback) => {
          // NEVER CACHE 13+! It's hard to get rid of them
          if (parseInt(req.z) > 13) {
            return callback(null)
          }

          // Write the tile to Redis
          client.set(key(req), buffer)
          callback()
        }
    }
}
