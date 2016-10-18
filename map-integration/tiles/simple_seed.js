var args = require('minimist')(process.argv.slice(2))
var config = require('./config')
var seeder = require('./seeder')
var async = require('async')

if (!args.hasOwnProperty('source_id')) {
  console.log('A source_id is required')
  process.exit(1)
}

if (args.hasOwnProperty('layers')) {
  args.layers = args.layers.split(',')
} else {
  args['layers'] = config.layers
}
seeder.validateSource(args.source_id, function(error, found) {
  if (error || !found) {
    console.log('Target source could not be found')
    process.exit(1)
  }
  async.eachLimit(args.layers, 1, function(layer, callback) {
    console.log(layer)
    seeder({
      target: 'source',
      source_id: [args.source_id],
      tileType: 'raster',
      tileSet: layer
    }, function() {
      callback()
    })
  }, function() {
    process.exit(0)
  })
})
