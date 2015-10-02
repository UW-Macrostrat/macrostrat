var fs = require('fs-extra');

module.exports = function(options) {
    function tilePath(directory, z, x, y, filename) {
      return directory + '/' + z + '/' + x + '/' + y + '/' + filename;
    }

    return {
        init: function(server, callback) {
            callback();
        },

        get: function(server, tile, callback) {

          function done(err, buffer, headers, refresh) {
        		return callback(err, buffer||null, headers, refresh);
        	}

          function getTile(tile_path) {
            fs.readFile(tile_path, function(error, buffer) {
              if (error) {
                return callback(error);
              }
              return callback(null, buffer, {'Content-Type': 'image/png'});
            });
          }

          // Check if file exists
          var file = tilePath(options.dir, tile.z, tile.x, tile.y, tile.filename);

          fs.stat(file, function(error, stat) {
            if (error) {
              if (tile.z < 11) {
                // Send blank tile
                return getTile(options.defaultTile);
              } else {
                return callback(error);
              }
            } else {
              return getTile(file);
            }
          });
        },

        set: function(server, req, buffer, headers, callback) {
          var file = tilePath(options.dir, req.z, req.x, req.y, req.filename);
        	fs.outputFile(file, buffer, callback);
        }
    }
}
