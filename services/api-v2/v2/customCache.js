var fs = require('fs-extra');
var SyncCache = require('active-cache/sync');
var filesizeParser = require('filesize-parser');

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

    var lruopts = {max: 6};

  	if (typeof options.size === 'string') {
  		lruopts.max = filesizeParser(options.size);
  		lruopts.length = function(item){ return item.buffer.length; };
  	} else if (typeof options.size === 'number') {
  		lruopts.max = options.size;
  	}

  	lruopts.maxAge = (options.ttl || 15) * 1000;
  	lruopts.interval = options.clearInterval || 5000;

  	var cache = new SyncCache(lruopts);

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
            return callback(null, item.buffer, item.headers);
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
          cache.set(key(tile), {buffer: buffer, headers: headers});

          // Write the tile to disk
        	fs.outputFile(file, buffer, callback);
        }
    }
}
