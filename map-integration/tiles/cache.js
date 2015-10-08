/*
  This is a cache based on
  tilestrata-disk - https://github.com/naturalatlas/tilestrata-disk

  It differs in that it never serves from disk, and always overwrites the cache
*/
var fs = require('fs');
var mkdirp = require('mkdirp');

module.exports = function(options) {

    function tilePath(directory, z, x, y, filename) {
      return directory + '/' + z + '/' + x + '/' + y + '/' + filename;
    }

    return {
        init: function(server, callback) {
            callback();
        },

        get: function(server, tile, callback) {
          callback('None');
        },

        set: function(server, req, buffer, headers, callback) {
          // Get the full tile path
          var file = tilePath(options.dir, req.z, req.x, req.y, req.filename);

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
