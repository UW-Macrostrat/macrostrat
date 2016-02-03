(function() {
  var fs = require('fs');
  var mapnik = require('tilestrata-mapnik');
  var mkdirp = require('mkdirp');
  var config = require('./config');

  var providers = {};

  // Create a tile provider for each scale that we precache
  config.seedScales.forEach(function(scale) {
    providers[scale] = mapnik({
        pathname: config.configPath + 'burwell_' + scale + '.xml',
        tileSize: 512,
        scale: 2
    })
  });

  function tilePath(directory, z, x, y, filename) {
    return directory + '/' + z + '/' + x + '/' + y + '/' + filename;
  }

  function rollTile(scale, tile, callback) {
    providers[scale].serve(null, tile, function(error, buffer) {
      // Get the full tile path
      var file = tilePath(config.cachePath, tile.z, tile.x, tile.y, 'tile.png');

      // Make sure the correct directory exists
      mkdirp(config.cachePath + '/' + tile.z + '/' + tile.x + '/' + tile.y, function(error) {

        // Write the tile to disk
        fs.writeFile(file, buffer, function(err) {
          if (err) {
            console.log('Error writing tile - ', err);
          }
          callback();
        });
      });
    });
  }

  Object.keys(providers).forEach(function(provider) {
    providers[provider].init(null, function() {
      //console.log('Initialized ', provider);
    });
  });

  module.exports = rollTile;

}());
