/*
  This is a hybrid memory/disk cache based on
  tilestrata-lru - https://github.com/naturalatlas/tilestrata-lru
  &
  tilestrata-disk - https://github.com/naturalatlas/tilestrata-disk
*/
var fs = require('fs');
var mkdirp = require('mkdirp');
var filesizeParser = require('filesize-parser');
var LRU = require('lru-cache');

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

    // Default to a max cache size of 1gb, and a max age of 6 hours
    var lruOptions = {
      max: (typeof(options.size) === 'string') ? filesizeParser(options.size) : 1000000000,
      maxAge: options.lruMaxAge || 21600000,
      length: function(item) {
        return item.buffer.length;
      }
    }
    // Define the cache
    var cache = LRU(lruOptions);

    var diskMaxAge = options.diskMaxAge || 86400000;

    return {
        init: function(server, callback) {
            callback();
        },

        get: function(server, tile, callback) {
          // Get the full tile path
          var file = tilePath(options.dir, tile.z, tile.x, tile.y, tile.filename);

          // Check if tile exists in memory
          var item = cache.get(key(tile));

          // if yes, return it
          if (item) {
            item.headers['X-MemoryCache-Hit'] = true;
            return callback(null, item.buffer, item.headers);
          }

          // if no, check the disk cache
          fs.stat(file, function(error, stat) {
            if (error || (z >= 11 && new Date() - stat.mtime.getTime() > diskMaxAge)) {
              // If it doesn't exist or it is too old and z < 11, return a blank tile
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
                cache.set(key(tile), {buffer: buffer, headers: headers});
                return callback(null, buffer, headers);
              });
            }
          });
        },

        set: function(server, req, buffer, headers, callback) {
          // Get the full tile path
          var file = tilePath(options.dir, req.z, req.x, req.y, req.filename);

          // Write the tile to cache
          cache.set(key(req), {buffer: buffer, headers: headers});

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
