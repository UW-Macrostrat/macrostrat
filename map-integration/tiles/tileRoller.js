(function() {
  var fs = require('fs');
  var async = require('async');
  var mapnik = require('tilestrata-mapnik');
  var vtile = require('tilestrata-vtile');
  var mkdirp = require('mkdirp');
  var config = require('./config');

  var providers = {};

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
    providers[scale].serve(null, tile, function(error, buffer) {
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


  module.exports.init = function(layer, type, callback) {
    async.series([
      // Set up the tile providers depending on what type of tiles are being created
      function(callback) {
        async.each(config.seedScales, function(scale, cb) {
          if (type === 'raster') {
            providers[scale] = mapnik({
                pathname: config.configPath + 'compiled_styles/burwell_' + scale + '_' + layer + '.xml',
                tileSize: 512,
                scale: 2
            });
          } else {
            providers[scale] = vtile({
                xml: config.configPath + 'compiled_styles/burwell_' + scale + '_' + layer + '.xml',
                tileSize: 256,
                metatile: 1,
                bufferSize: 128
            });
          }

          cb(null);

        }, function() {
          callback(null);
        });
      },

      // Initialize the newly created providers
      function(callback) {
        async.each(Object.keys(providers), function(provider, cb) {
          providers[provider].init(null, function() {
            console.log('Initialized ', provider);
            cb(null);
          });
        }, function() {
          callback(null);
        });
      }
    // Be done
    ], function() {
      callback();
    });
  }

}());
