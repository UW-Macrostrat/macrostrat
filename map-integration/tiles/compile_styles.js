var config = require('./config');
var setup = require('./setup');
var async = require('async');

async.eachLimit(config.layers, 1, function(layer, callback) {
  console.log(layer)
  setup(layer, function(error) {
    if (error) return callback(error);
    callback(null);
  });
}, function(error) {
  if (error) console.log(error);

  process.exit(0)
  console.log('Configuration files generated');
});
