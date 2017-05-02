var args = require('minimist')(process.argv.slice(2))
var config = require('./config')
var seeder = require('./seeder')
var async = require('async')

var layer = 'emphasized'

if (!args.hasOwnProperty('source_id')) {
  console.log('A source_id is required')
  process.exit(1)
}

seeder.validateSource(args.source_id, function(error, found) {
  if (error || !found) {
    console.log('Target source could not be found')
    process.exit(1)
  }
  async.eachLimit(['vector', 'raster'], 1, function(tileType, callback) {
    console.log(tileType)
    seeder({
      target: 'source',
      source_id: [args.source_id],
      tileType: tileType,
      tileSet: layer
    }, function() {
      callback()
    })
  }, function() {
    process.exit(0)
  })
})
