'use strict'

const async = require('async')
const fs = require('fs')
const mkdirp = require('mkdirp')
const redis = require('redis')
const client = redis.createClient(6379, '127.0.0.1', {'return_buffers': true})
const secret = require('./credentials').secret

module.exports = (options) => {

    function tilePath(directory, z, x, y, format) {
      return `${directory}/${z}/${x}/${y}${format}`
    }

    function key(req) {
      return `${req.z},${req.x},${req.y},${req.layer},${req.filename}`
    }

    let blankVectorTile = ''
    let blankRasterTile = ''

    fs.readFile(`${__dirname}/resources/tile.png`, (error, buffer) => {
      blankRasterTile = buffer
    })
    fs.readFile(`${__dirname}/resources/tile.mvt`, (error, buffer) => {
      blankVectorTile = buffer
    })

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
      let file = tilePath(options.dir, tile.z, tile.x, tile.y, tile.filename.replace('*', ''))

      // Errors will be thrown if we try to delete a tile that doesn't exist, but 🤷‍♂️
      async.parallel([
        (done) => {
          fs.unlink(file, (error) => {
            done()
          })
        },
        (done) => {
          client.del(key(tile), (error) => {
            done(null)
          })
        }
      ], (error) => {
        // Doneski. Don't care if it failed or not
        callback(null)
      })
    }

    function getTile(tilePath, cb) {
      fs.readFile(tilePath, (error, buffer) => {
        if (error) {
          return cb(error)
        }
        let headers = (tilePath.indexOf('.png') > -1) ? getHeaders('raster') : getHeaders('vector')

        headers['X-TileStrata-DiskHit'] = 1
        return cb(null, buffer, headers)
      })
    }

    return {
        init: (server, callback) => {
          callback()
        },

        get: (server, tile, callback) => {
          // I know it is jank to delete something with a GET request, but it is also expedient and easy
          if (tile.headers['x-tilestrata-deletetile'] && tile.headers['x-tilestrata-deletetile'] === secret) {
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

            // Get the full tile path
            var file = tilePath(options.dir, tile.z, tile.x, tile.y, tile.filename.replace('*', ''))

            // if no, check the disk cache
            fs.stat(file, (error, stat) => {
              if (error) {
                return callback(null)
                // If it doesn't exist at z < 11, return a blank tile
                // if (tile.z < 11) {
                //   // Send blank tile
                //   getTile(options.defaultTile, (error, buffer, headers) => {
                //     if (error) {
                //       return callback(error)
                //     }
                //     return callback(null, buffer, headers)
                //   })
                //
                // // If z >= 11 and no tile exists, create one (which will then write it to disk for next time)
                // } else {
                //   return callback(error)
                // }

              // If it does exist in the disk cache, spit it back
              } else {
                getTile(file, (error, buffer, headers) => {
                  if (error) {
                    return callback(error)
                  }

                  // Put the tile into the Redis cache
                  client.set(key(tile), buffer)

                  return callback(null, buffer, headers)
                })
              }
            })
          })
        },

        set: (server, req, buffer, headers, callback) => {
          // NEVER CACHE 13+! It's hard to get rid of them
          if (parseInt(req.z) > 13) {
            return callback(null)
          }

          // Write the tile to cache
          client.set(key(req), buffer)

          // Make sure the correct directory exists
          mkdirp(`${options.dir}/${req.z}/${req.x}`, (error) => {

            // Get the full tile path
            var file = tilePath(options.dir, req.z, req.x, req.y, req.filename.replace('*', ''))

            // Write the tile to disk
            fs.writeFile(file, buffer, (err) => {
              if (err) {
                console.log('Error writing tile - ', err)
              }
              callback()
            })
          })
        }
    }
}
