/*
  This is a hybrid memory/disk cache based on
  tilestrata-lru - https://github.com/naturalatlas/tilestrata-lru
  &
  tilestrata-disk - https://github.com/naturalatlas/tilestrata-disk
*/
var fs = require('fs');
var mkdirp = require('mkdirp');
var redis = require('redis');
var client = redis.createClient(6379, '127.0.0.1', {'return_buffers': true});

module.exports = function(options) {

    function tilePath(directory, z, x, y, filename) {
      return directory + '/' + z + '/' + x + '/' + y + '/' + filename;
    }

    function key(req) {
    	return req.z + ',' + req.x + ',' + req.y + ',' + req.layer + ',' + req.filename;
    }

    function getTile(tilePath, cb) {
      fs.readFile(tilePath, function(error, buffer) {
        if (error) {
          return cb(error);
        }
        return cb(null, buffer, {'Content-Type': 'image/png'});
      });
    }

    return {
        init: function(server, callback) {
          callback();
        },

        get: function(server, tile, callback) {

          // Get the full tile path
          var file = tilePath(options.dir, tile.z, tile.x, tile.y, tile.filename);

          // Check if tile exists in memory
          client.get(key(tile), function(error, data) {
            // if yes, return it
            if (data) {
              return callback(null, data, {
                'Content-Type': 'image/png',
                'X-TileStrata-RedisHit': '1',
                'X-Powered-By': 'TileStrata/2.0.1',
                'Cache-Control': 'max-age=60'
              });
            }

            // if no, check the disk cache
            fs.stat(file, function(error, stat) {
              if (error) {
                // If it doesn't exist and z < 11, return a blank tile
                if (tile.z < 11) {
                  // Send blank tile
                  getTile(options.defaultTile, function(error, buffer, headers) {
                    if (error) {
                      return callback(error)
                    }
                    return callback(null, buffer, headers);
                  });

                // If z >= 11 and no tile exists, create one (which will then write it to disk for next time)
                } else {
                  return callback(error);
                }

              // If it does exist in the disk cache, spit it back
              } else {
                getTile(file, function(error, buffer, headers) {
                  if (error) {
                    return callback(error)
                  }

                  // Put the tile into the Redis cache
                  client.set(key(tile), buffer);

                  return callback(null, buffer, headers);
                });
              }
            });
          });

        },

        set: function(server, req, buffer, headers, callback) {
          // Get the full tile path
          var file = tilePath(options.dir, req.z, req.x, req.y, req.filename);

          // Write the tile to cache
          client.set(key(req), buffer);

          // Make sure the correct directory exists
          mkdirp(options.dir + '/' + req.z + '/' + req.x + '/' + req.y, function(error) {

            // Write the tile to disk
            fs.writeFile(file, buffer, function(err) {
              if (err) {
                console.log('Error writing tile - ', err);
              }
              callback();
            });
          });
        }
    }
}
