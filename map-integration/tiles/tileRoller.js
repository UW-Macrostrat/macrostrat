(function() {
  var fs = require('fs');
  var mapnik = require('tilestrata-mapnik');
  var vtile = require('tilestrata-vtile');
  var mkdirp = require('mkdirp');
  var config = require('./config');

  var providers = {};
  var vectorProviders = {};

  // Create a tile provider for each scale that we precache
  config.seedScales.forEach(function(scale) {
    providers[scale] = mapnik({
        pathname: config.configPath + 'burwell_' + scale + '.xml',
        tileSize: 512,
        scale: 2
    });

    vectorProviders[scale] = vtile({
        xml: config.configPath + '/burwell_' + scale + '.xml',
        tileSize: 256,
        metatile: 1,
        bufferSize: 128
    });
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

  function rollVectorTile(scale, tile, callback) {
    vectorProviders[scale].serve(null, tile, function(error, buffer) {
      // Get the full tile path
      var file = tilePath(config.cachePathVector, tile.z, tile.x, tile.y, 'tile.mvt');

      // Make sure the correct directory exists
      mkdirp(config.cachePathVector + '/' + tile.z + '/' + tile.x + '/' + tile.y, function(error) {

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

  module.exports.roll = {
    vector: rollVectorTile,
    raster: rollTile
  };

  module.exports.init = function(callback) {
    Object.keys(providers).forEach(function(provider) {
      providers[provider].init(null, function() {
        console.log('Initialized ', provider);
      });
      vectorProviders[provider].init(null, function() {
        console.log('Initialized vector ', provider);
      });
    });

    callback();
  }

}());
