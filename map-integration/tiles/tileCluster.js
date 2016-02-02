var cluster = require('cluster');

if (cluster.isMaster) {
  //var numWorkers = require('os').cpus().length;
  var numWorkers = 3;

  console.log('Master cluster setting up ' + numWorkers + ' workers...');

  for(var i = 0; i < numWorkers; i++) {
      cluster.fork();
  }

  cluster.on('online', function(worker) {
      console.log('Worker ' + worker.process.pid + ' is online');
  });

  cluster.on('exit', function(worker, code, signal) {
      console.log('Worker ' + worker.process.pid + ' died with code: ' + code + ', and signal: ' + signal);
      console.log('Starting a new worker');
      cluster.fork();
  });
} else {
  // Depdendencies for tile server
  var tilestrata = require('tilestrata');
  var mapnik = require('tilestrata-mapnik');
  var cache = require('./cache');

  // Depdendencies for tile seeding

  var config = require('./config');

  function resHook(options) {
      return {
          name: 'responseHook',
          init: function(server, callback) {
              callback();
          },
          reshook: function(server, tile, req, res, result, callback) {
              console.log(req.url);
              callback();
          },
          destroy: function(server, callback) {
              callback();
          }
      }
  };

  // Define the tileserver that will be used for cache seedings
  var strata = tilestrata();

  // define layers
  strata.layer('burwell_tiny')
      .route('tile.png')
          .use(resHook())
          .use(cache({dir: config.cachePath}))
          .use(mapnik({
              pathname: config.configPath + 'burwell_tiny.xml',
              tileSize: 512,
              scale: 2
          }));

  strata.layer('burwell_small')
      .route('tile.png')
          .use(cache({dir: config.cachePath}))
          .use(mapnik({
              pathname: config.configPath + 'burwell_small.xml',
              tileSize: 512,
              scale: 2
          }));

  strata.layer('burwell_medium')
      .route('tile.png')
          .use(cache({dir: config.cachePath}))
          .use(mapnik({
              pathname: config.configPath + 'burwell_medium.xml',
              tileSize: 512,
              scale: 2
          }));

  strata.layer('burwell_large')
      .route('tile.png')
          .use(cache({dir: config.cachePath}))
          .use(mapnik({
              pathname: config.configPath + 'burwell_large.xml',
              tileSize: 512,
              scale: 2
          }));

  // start accepting requests
  strata.listen(config.port);

}
