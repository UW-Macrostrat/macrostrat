(function() {
  var path = require('path')
  var fs = require('fs');
  var async = require('async');
  var mapnik = require('tilestrata-mapnik');
  var vtile = require('tilestrata-vtile');
  var portscanner = require('portscanner');
  var mkdirp = require('mkdirp');
  var config = require('./config');
  var yaml = require('yamljs')
  var credentials = yaml.load(path.join(__dirname, '.', 'credentials.yml'))

  var providers = {};
  var mapType = '';


  function tilePath(directory, z, x, y, filename) {
    // No mapType means we are rolling vector tiles
    if (mapType) {
      return directory + '/' + mapType + '/' + z + '/' + x + '/' + y + '/' + filename;
    } else {
      return directory + '/' + z + '/' + x + '/' + y + '/' + filename;
    }

  }

  function rollTile(scale, tile, callback) {
    providers[scale].serve(null, tile, function(error, buffer) {
      // Get the full tile path
      var file = tilePath(credentials.cache_path, tile.z, tile.x, tile.y, 'tile.png');

      try {
        var redisKey = `${tile.z},${tile.x},${tile.y},${mapType},tile.png`;
        client.get(redisKey, function(error, data) {
          if (data) {
            client.set(redisKey, buffer);
          }
        });
      } catch(er) {

      }

      // Make sure the correct directory exists
      mkdirp(credentials.cache_path + '/' + mapType + '/' + tile.z + '/' + tile.x + '/' + tile.y, function(error) {

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
      var file = tilePath(credentials.cache_pathVector, tile.z, tile.x, tile.y, 'tile.pbf');

      // Make sure the correct directory exists
      mkdirp(credentials.cache_pathVector + '/' + tile.z + '/' + tile.x + '/' + tile.y, function(error) {

        // Write the tile to disk
        fs.writeFile(file, buffer, function(err) {
          if (err) {
            console.log('Error writing tile - ', err);
            throw new Error('Could not write to tilepath')
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
    mapType = layer;

    async.series([
      function(callback) {
        setTimeout(function() {
          portscanner.checkPortStatus(credentials.redis_port, '127.0.0.1', function(error, status) {
              if (status === 'open') {
                console.log('Redis available - cache will be updated')
                redis = require('redis');
                client = redis.createClient(credentials.redis_port, '127.0.0.1', {'return_buffers': true});
              }

              callback(null);
          });
        }, 10);
      },

      // Set up the tile providers depending on what type of tiles are being created
      function(callback) {
        async.each(config.seedScales, function(scale, cb) {
          if (type === 'raster') {
            providers[scale] = mapnik({
                pathname: config.configPath + 'compiled_styles/burwell_' + scale + '_' + layer + '.xml',
                tileSize: 512,
                scale: 2,
                metatile: 1
            });
          } else {
            providers[scale] = vtile({
                xml: config.configPath + 'compiled_styles/burwell_vtile_' + scale + '.xml',
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
          providers[provider].init(null, function(error) {
            if (error) {
              console.log(error)
              process.exit(1)
            }
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
